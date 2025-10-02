"""
Unit tests for HeadlessConfiguration state transitions.

This module tests the state management and transitions of the HeadlessConfiguration
data model, including retry attempts, fallback modes, and effective mode calculation.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'EXPERIMENTAL'))

from corelib.models import HeadlessConfiguration


class TestHeadlessConfigurationStateTransitions:
    """Test state transitions for HeadlessConfiguration."""
    
    def test_initial_enabled_state(self):
        """Test initial state with headless enabled."""
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        
        assert config.enabled == True
        assert config.source == "interactive_setup"
        assert config.retry_attempted == False
        assert config.fallback_to_visible == False
        assert config.get_effective_headless_mode() == True
    
    def test_initial_disabled_state(self):
        """Test initial state with headless disabled."""
        config = HeadlessConfiguration(enabled=False, source="interactive_setup")
        
        assert config.enabled == False
        assert config.source == "interactive_setup"
        assert config.retry_attempted == False
        assert config.fallback_to_visible == False
        assert config.get_effective_headless_mode() == False
    
    def test_mark_retry_attempted_transition(self):
        """Test transition to retry attempted state."""
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        
        retry_config = config.mark_retry_attempted()
        
        # Original config unchanged
        assert config.retry_attempted == False
        
        # New config has retry marked
        assert retry_config.enabled == True
        assert retry_config.retry_attempted == True
        assert retry_config.fallback_to_visible == False
        assert retry_config.get_effective_headless_mode() == True
    
    def test_mark_fallback_to_visible_transition(self):
        """Test transition to fallback visible state."""
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        retry_config = config.mark_retry_attempted()
        
        fallback_config = retry_config.mark_fallback_to_visible()
        
        # Original configs unchanged
        assert config.fallback_to_visible == False
        assert retry_config.fallback_to_visible == False
        
        # New config has fallback marked
        assert fallback_config.enabled == False  # Changed to False in fallback
        assert fallback_config.retry_attempted == True
        assert fallback_config.fallback_to_visible == True
        assert fallback_config.get_effective_headless_mode() == False
    
    def test_fallback_without_retry_raises_error(self):
        """Test that fallback without retry attempt raises ValueError."""
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        
        with pytest.raises(ValueError, match="Cannot fallback to visible without retry attempt"):
            config.mark_fallback_to_visible()
    
    def test_effective_headless_mode_with_fallback(self):
        """Test effective mode calculation respects fallback state."""
        # Start with enabled headless
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        assert config.get_effective_headless_mode() == True
        
        # After retry, still headless
        retry_config = config.mark_retry_attempted()
        assert retry_config.get_effective_headless_mode() == True
        
        # After fallback, becomes visible
        fallback_config = retry_config.mark_fallback_to_visible()
        assert fallback_config.get_effective_headless_mode() == False
    
    def test_string_representation_states(self):
        """Test string representation for different states."""
        # Initial state
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        assert "headless mode" in str(config)
        
        # After retry
        retry_config = config.mark_retry_attempted()
        assert "headless mode (retry attempted)" in str(retry_config)
        
        # After fallback
        fallback_config = retry_config.mark_fallback_to_visible()
        assert "visible mode (retry attempted, fallback to visible)" in str(fallback_config)
    
    def test_immutability_of_state_transitions(self):
        """Test that state transitions create new instances and don't modify originals."""
        original = HeadlessConfiguration(enabled=True, source="interactive_setup")
        original_id = id(original)
        
        retry = original.mark_retry_attempted()
        retry_id = id(retry)
        
        fallback = retry.mark_fallback_to_visible()
        fallback_id = id(fallback)
        
        # All instances are different objects
        assert original_id != retry_id
        assert retry_id != fallback_id
        assert original_id != fallback_id
        
        # Original state preserved
        assert original.retry_attempted == False
        assert original.fallback_to_visible == False
        assert original.enabled == True
    
    def test_validation_enabled_must_be_boolean(self):
        """Test that enabled parameter must be boolean."""
        with pytest.raises(ValueError, match="enabled must be boolean"):
            HeadlessConfiguration(enabled="true", source="interactive_setup")
    
    def test_validation_source_must_be_interactive_setup(self):
        """Test that source must be 'interactive_setup'."""
        with pytest.raises(ValueError, match="source must equal 'interactive_setup'"):
            HeadlessConfiguration(enabled=True, source="environment")
    
    def test_validation_retry_attempted_must_be_boolean(self):
        """Test that retry_attempted must be boolean."""
        with pytest.raises(ValueError, match="retry_attempted must be boolean"):
            HeadlessConfiguration(
                enabled=True, 
                source="interactive_setup",
                retry_attempted="yes"
            )
    
    def test_validation_fallback_to_visible_must_be_boolean(self):
        """Test that fallback_to_visible must be boolean.""" 
        with pytest.raises(ValueError, match="fallback_to_visible must be boolean"):
            HeadlessConfiguration(
                enabled=True,
                source="interactive_setup", 
                retry_attempted=True,
                fallback_to_visible="no"
            )
    
    def test_validation_fallback_requires_retry(self):
        """Test that fallback_to_visible requires retry_attempted=True."""
        with pytest.raises(ValueError, match="fallback_to_visible only valid if retry_attempted is True"):
            HeadlessConfiguration(
                enabled=True,
                source="interactive_setup",
                retry_attempted=False,
                fallback_to_visible=True
            )


class TestHeadlessConfigurationEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_complex_state_transition_sequence(self):
        """Test a complex sequence of state transitions."""
        # Start with disabled mode
        config = HeadlessConfiguration(enabled=False, source="interactive_setup")
        assert config.get_effective_headless_mode() == False
        
        # Mark retry attempted (still disabled)
        retry_config = config.mark_retry_attempted()
        assert retry_config.get_effective_headless_mode() == False
        
        # Mark fallback (should remain disabled)
        fallback_config = retry_config.mark_fallback_to_visible()
        assert fallback_config.get_effective_headless_mode() == False
        assert fallback_config.enabled == False
        assert fallback_config.fallback_to_visible == True
    
    def test_multiple_retry_attempts_immutable(self):
        """Test that multiple retry attempts don't affect each other."""
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        
        retry1 = config.mark_retry_attempted()
        retry2 = config.mark_retry_attempted()
        
        # Both retry configs should be identical but separate objects
        assert id(retry1) != id(retry2)
        assert retry1.retry_attempted == retry2.retry_attempted == True
        assert retry1.enabled == retry2.enabled == True
        assert retry1.fallback_to_visible == retry2.fallback_to_visible == False
    
    def test_state_consistency_after_transitions(self):
        """Test that all state properties remain consistent after transitions."""
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        
        # Go through full transition sequence
        retry_config = config.mark_retry_attempted()
        fallback_config = retry_config.mark_fallback_to_visible()
        
        # Verify source is preserved throughout
        assert config.source == "interactive_setup"
        assert retry_config.source == "interactive_setup"
        assert fallback_config.source == "interactive_setup"
        
        # Verify retry state is preserved in fallback
        assert fallback_config.retry_attempted == True
        
        # Verify fallback changes enabled to False
        assert fallback_config.enabled == False