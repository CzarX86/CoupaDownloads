"""
EmbeddingGemma Use Case Examples for CoupaDownloads
Practical examples of how EmbeddingGemma could enhance the MyScript system
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import pandas as pd

# Import our assessment framework
from capability_assessment import EmbeddingGemmaCapabilityAssessment
from config import get_config


@dataclass
class UseCaseResult:
    """Result of a use case demonstration."""
    use_case: str
    success: bool
    performance_metrics: Dict[str, Any]
    business_value: str
    implementation_complexity: str
    recommendations: List[str]


class CoupaDownloadsUseCases:
    """Demonstration of EmbeddingGemma use cases for CoupaDownloads."""
    
    def __init__(self):
        self.config = get_config()
        self.assessment = EmbeddingGemmaCapabilityAssessment()
        
        # Load model if available
        self.model = None
        if hasattr(self.assessment, 'model') and self.assessment.model:
            self.model = self.assessment.model
        
        # Sample Coupa data for demonstrations
        self._create_sample_data()
    
    def _create_sample_data(self):
        """Create sample Coupa data for demonstrations."""
        self.sample_pos = [
            {
                "po_number": "PO-12345",
                "description": "Office supplies including pens, paper, notebooks, and staplers",
                "vendor": "Office Depot",
                "amount": 1250.00,
                "attachments": ["invoice.pdf", "receipt.pdf"]
            },
            {
                "po_number": "PO-12346", 
                "description": "Software licenses for Microsoft Office, Adobe Creative Suite",
                "vendor": "Microsoft Corp",
                "amount": 5000.00,
                "attachments": ["license_agreement.pdf", "invoice.pdf"]
            },
            {
                "po_number": "PO-12347",
                "description": "IT equipment: laptops, monitors, networking gear",
                "vendor": "Dell Technologies",
                "amount": 15000.00,
                "attachments": ["quote.pdf", "specifications.pdf"]
            },
            {
                "po_number": "PO-12348",
                "description": "Office supplies: pens, paper, notebooks, staplers",
                "vendor": "Staples Inc",
                "amount": 800.00,
                "attachments": ["invoice.pdf"]
            },
            {
                "po_number": "PO-12349",
                "description": "Cloud hosting services: AWS, Azure, backup solutions",
                "vendor": "Amazon Web Services",
                "amount": 3000.00,
                "attachments": ["service_agreement.pdf", "pricing.pdf"]
            }
        ]
        
        self.sample_attachments = [
            "Purchase Order #12345 for office supplies including pens, paper, and notebooks.",
            "Software license agreement for Microsoft Office 365 Business Premium.",
            "Equipment quote for Dell Latitude laptops and monitors.",
            "Service contract for AWS cloud hosting and backup services.",
            "Invoice for office supplies: pens, paper, notebooks, and staplers.",
            "Contract agreement for IT consulting services and system maintenance.",
            "Receipt for travel expenses: flights, hotels, and meals.",
            "Training materials order: books, online courses, and certifications.",
            "Maintenance contract for office equipment and HVAC systems.",
            "Software development agreement for custom application development."
        ]
    
    def demonstrate_all_use_cases(self) -> List[UseCaseResult]:
        """Demonstrate all use cases for EmbeddingGemma in CoupaDownloads."""
        print("🎯 EmbeddingGemma Use Cases for CoupaDownloads")
        print("=" * 60)
        
        use_cases = [
            self.use_case_duplicate_detection,
            self.use_case_semantic_search,
            self.use_case_content_classification,
            self.use_case_vendor_similarity,
            self.use_case_attachment_analysis,
            self.use_case_rag_system
        ]
        
        results = []
        for use_case_func in use_cases:
            try:
                result = use_case_func()
                results.append(result)
                self._print_use_case_result(result)
            except Exception as e:
                print(f"❌ Use case {use_case_func.__name__} failed: {e}")
                results.append(UseCaseResult(
                    use_case=use_case_func.__name__,
                    success=False,
                    performance_metrics={},
                    business_value="Failed to demonstrate",
                    implementation_complexity="Unknown",
                    recommendations=[f"Fix error: {e}"]
                ))
        
        return results
    
    def use_case_duplicate_detection(self) -> UseCaseResult:
        """Use Case 1: Duplicate Purchase Order Detection."""
        print("\n🔍 Use Case 1: Duplicate Purchase Order Detection")
        
        if not self.model:
            return UseCaseResult(
                use_case="duplicate_detection",
                success=False,
                performance_metrics={},
                business_value="Could not demonstrate - model not available",
                implementation_complexity="Medium",
                recommendations=["Ensure EmbeddingGemma model is loaded"]
            )
        
        start_time = time.time()
        
        # Extract descriptions for similarity comparison
        descriptions = [po["description"] for po in self.sample_pos]
        
        # Generate embeddings
        embeddings = self.model.encode(descriptions)
        
        # Find similar pairs (potential duplicates)
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_matrix = cosine_similarity(embeddings)
        
        # Find pairs with high similarity (>0.8)
        duplicate_candidates = []
        for i in range(len(descriptions)):
            for j in range(i+1, len(descriptions)):
                similarity = similarity_matrix[i][j]
                if similarity > 0.8:
                    duplicate_candidates.append({
                        "po1": self.sample_pos[i]["po_number"],
                        "po2": self.sample_pos[j]["po_number"],
                        "similarity": similarity,
                        "description1": descriptions[i],
                        "description2": descriptions[j]
                    })
        
        duration = time.time() - start_time
        
        return UseCaseResult(
            use_case="duplicate_detection",
            success=True,
            performance_metrics={
                "processing_time": duration,
                "documents_processed": len(descriptions),
                "duplicate_candidates_found": len(duplicate_candidates),
                "average_similarity": float(similarity_matrix.mean())
            },
            business_value="Prevents duplicate purchases, saves money, improves compliance",
            implementation_complexity="Low",
            recommendations=[
                "Set similarity threshold based on business requirements",
                "Implement automated alerts for high-similarity POs",
                "Add manual review workflow for flagged duplicates"
            ]
        )
    
    def use_case_semantic_search(self) -> UseCaseResult:
        """Use Case 2: Semantic Search for Purchase Orders."""
        print("\n🔍 Use Case 2: Semantic Search for Purchase Orders")
        
        if not self.model:
            return UseCaseResult(
                use_case="semantic_search",
                success=False,
                performance_metrics={},
                business_value="Could not demonstrate - model not available",
                implementation_complexity="Medium",
                recommendations=["Ensure EmbeddingGemma model is loaded"]
            )
        
        start_time = time.time()
        
        # Create search queries
        search_queries = [
            "office supplies and stationery",
            "software and licenses",
            "computer equipment and hardware",
            "cloud services and hosting"
        ]
        
        # Generate embeddings for queries and documents
        query_embeddings = self.model.encode(search_queries)
        doc_embeddings = self.model.encode([po["description"] for po in self.sample_pos])
        
        # Calculate similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(query_embeddings, doc_embeddings)
        
        # Find best matches for each query
        search_results = []
        for i, query in enumerate(search_queries):
            best_matches = []
            for j, po in enumerate(self.sample_pos):
                similarity = similarities[i][j]
                if similarity > 0.3:  # Threshold for relevance
                    best_matches.append({
                        "po_number": po["po_number"],
                        "similarity": similarity,
                        "description": po["description"]
                    })
            
            # Sort by similarity
            best_matches.sort(key=lambda x: x["similarity"], reverse=True)
            search_results.append({
                "query": query,
                "matches": best_matches[:3]  # Top 3 matches
            })
        
        duration = time.time() - start_time
        
        return UseCaseResult(
            use_case="semantic_search",
            success=True,
            performance_metrics={
                "processing_time": duration,
                "queries_processed": len(search_queries),
                "documents_indexed": len(self.sample_pos),
                "average_matches_per_query": sum(len(r["matches"]) for r in search_results) / len(search_queries)
            },
            business_value="Enables natural language search, improves user experience, faster document discovery",
            implementation_complexity="Medium",
            recommendations=[
                "Implement search ranking algorithm",
                "Add search result caching",
                "Create search analytics dashboard"
            ]
        )
    
    def use_case_content_classification(self) -> UseCaseResult:
        """Use Case 3: Automatic Content Classification."""
        print("\n🔍 Use Case 3: Automatic Content Classification")
        
        if not self.model:
            return UseCaseResult(
                use_case="content_classification",
                success=False,
                performance_metrics={},
                business_value="Could not demonstrate - model not available",
                implementation_complexity="High",
                recommendations=["Ensure EmbeddingGemma model is loaded"]
            )
        
        start_time = time.time()
        
        # Define categories
        categories = {
            "office_supplies": "Office supplies, stationery, pens, paper, notebooks",
            "software": "Software licenses, applications, cloud services",
            "equipment": "Computer equipment, hardware, IT devices",
            "services": "Consulting, maintenance, support services",
            "travel": "Travel expenses, flights, hotels, meals"
        }
        
        # Generate embeddings for categories and documents
        category_descriptions = list(categories.values())
        category_embeddings = self.model.encode(category_descriptions)
        
        doc_descriptions = [po["description"] for po in self.sample_pos]
        doc_embeddings = self.model.encode(doc_descriptions)
        
        # Classify documents
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(doc_embeddings, category_embeddings)
        
        classifications = []
        for i, po in enumerate(self.sample_pos):
            best_category_idx = similarities[i].argmax()
            best_category = list(categories.keys())[best_category_idx]
            confidence = similarities[i][best_category_idx]
            
            classifications.append({
                "po_number": po["po_number"],
                "predicted_category": best_category,
                "confidence": confidence,
                "description": po["description"]
            })
        
        duration = time.time() - start_time
        
        return UseCaseResult(
            use_case="content_classification",
            success=True,
            performance_metrics={
                "processing_time": duration,
                "documents_classified": len(classifications),
                "categories_defined": len(categories),
                "average_confidence": sum(c["confidence"] for c in classifications) / len(classifications)
            },
            business_value="Automates categorization, improves data organization, enables better reporting",
            implementation_complexity="High",
            recommendations=[
                "Fine-tune categories based on business needs",
                "Implement confidence thresholds",
                "Add manual override capabilities"
            ]
        )
    
    def use_case_vendor_similarity(self) -> UseCaseResult:
        """Use Case 4: Vendor Similarity Analysis."""
        print("\n🔍 Use Case 4: Vendor Similarity Analysis")
        
        if not self.model:
            return UseCaseResult(
                use_case="vendor_similarity",
                success=False,
                performance_metrics={},
                business_value="Could not demonstrate - model not available",
                implementation_complexity="Medium",
                recommendations=["Ensure EmbeddingGemma model is loaded"]
            )
        
        start_time = time.time()
        
        # Create vendor profiles with their typical products/services
        vendor_profiles = {
            "Office Depot": "Office supplies, stationery, furniture, business services",
            "Microsoft Corp": "Software licenses, cloud services, productivity tools",
            "Dell Technologies": "Computer hardware, laptops, servers, IT equipment",
            "Staples Inc": "Office supplies, printing services, business solutions",
            "Amazon Web Services": "Cloud computing, hosting, storage, IT services"
        }
        
        # Generate embeddings for vendor profiles
        profile_descriptions = list(vendor_profiles.values())
        profile_embeddings = self.model.encode(profile_descriptions)
        
        # Analyze PO descriptions against vendor profiles
        po_descriptions = [po["description"] for po in self.sample_pos]
        po_embeddings = self.model.encode(po_descriptions)
        
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(po_embeddings, profile_embeddings)
        
        vendor_analysis = []
        for i, po in enumerate(self.sample_pos):
            best_vendor_idx = similarities[i].argmax()
            best_vendor = list(vendor_profiles.keys())[best_vendor_idx]
            confidence = similarities[i][best_vendor_idx]
            
            vendor_analysis.append({
                "po_number": po["po_number"],
                "current_vendor": po["vendor"],
                "recommended_vendor": best_vendor,
                "confidence": confidence,
                "match": po["vendor"] == best_vendor
            })
        
        duration = time.time() - start_time
        
        return UseCaseResult(
            use_case="vendor_similarity",
            success=True,
            performance_metrics={
                "processing_time": duration,
                "pos_analyzed": len(vendor_analysis),
                "vendors_profiled": len(vendor_profiles),
                "correct_matches": sum(1 for v in vendor_analysis if v["match"]),
                "match_accuracy": sum(1 for v in vendor_analysis if v["match"]) / len(vendor_analysis)
            },
            business_value="Optimizes vendor selection, identifies cost savings opportunities, improves procurement efficiency",
            implementation_complexity="Medium",
            recommendations=[
                "Build comprehensive vendor profiles",
                "Implement vendor recommendation engine",
                "Add cost analysis integration"
            ]
        )
    
    def use_case_attachment_analysis(self) -> UseCaseResult:
        """Use Case 5: Attachment Content Analysis."""
        print("\n🔍 Use Case 5: Attachment Content Analysis")
        
        if not self.model:
            return UseCaseResult(
                use_case="attachment_analysis",
                success=False,
                performance_metrics={},
                business_value="Could not demonstrate - model not available",
                implementation_complexity="High",
                recommendations=["Ensure EmbeddingGemma model is loaded"]
            )
        
        start_time = time.time()
        
        # Generate embeddings for attachment descriptions
        attachment_embeddings = self.model.encode(self.sample_attachments)
        
        # Define attachment types
        attachment_types = {
            "invoice": "Invoice, billing, payment, cost",
            "contract": "Contract, agreement, terms, conditions",
            "quote": "Quote, proposal, estimate, pricing",
            "receipt": "Receipt, proof of purchase, transaction",
            "specification": "Specification, technical details, requirements"
        }
        
        type_descriptions = list(attachment_types.values())
        type_embeddings = self.model.encode(type_descriptions)
        
        # Classify attachments
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(attachment_embeddings, type_embeddings)
        
        classifications = []
        for i, attachment in enumerate(self.sample_attachments):
            best_type_idx = similarities[i].argmax()
            best_type = list(attachment_types.keys())[best_type_idx]
            confidence = similarities[i][best_type_idx]
            
            classifications.append({
                "attachment_text": attachment[:50] + "...",
                "predicted_type": best_type,
                "confidence": confidence
            })
        
        duration = time.time() - start_time
        
        return UseCaseResult(
            use_case="attachment_analysis",
            success=True,
            performance_metrics={
                "processing_time": duration,
                "attachments_analyzed": len(classifications),
                "types_defined": len(attachment_types),
                "average_confidence": sum(c["confidence"] for c in classifications) / len(classifications)
            },
            business_value="Automates document processing, improves compliance, enables better document management",
            implementation_complexity="High",
            recommendations=[
                "Integrate with OCR for scanned documents",
                "Implement document extraction pipeline",
                "Add compliance checking capabilities"
            ]
        )
    
    def use_case_rag_system(self) -> UseCaseResult:
        """Use Case 6: RAG System for Document Q&A."""
        print("\n🔍 Use Case 6: RAG System for Document Q&A")
        
        if not self.model:
            return UseCaseResult(
                use_case="rag_system",
                success=False,
                performance_metrics={},
                business_value="Could not demonstrate - model not available",
                implementation_complexity="Very High",
                recommendations=["Ensure EmbeddingGemma model is loaded"]
            )
        
        start_time = time.time()
        
        # Create a knowledge base from PO data
        knowledge_base = []
        for po in self.sample_pos:
            knowledge_base.append(f"PO {po['po_number']}: {po['description']} from {po['vendor']} for ${po['amount']}")
        
        # Generate embeddings for knowledge base
        kb_embeddings = self.model.encode(knowledge_base)
        
        # Sample questions
        questions = [
            "What office supplies were purchased recently?",
            "Which vendor provides software licenses?",
            "What is the total amount spent on IT equipment?",
            "Are there any duplicate purchases?"
        ]
        
        # Generate embeddings for questions
        question_embeddings = self.model.encode(questions)
        
        # Find relevant documents for each question
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(question_embeddings, kb_embeddings)
        
        qa_results = []
        for i, question in enumerate(questions):
            # Find top 3 most relevant documents
            top_indices = similarities[i].argsort()[-3:][::-1]
            relevant_docs = [knowledge_base[idx] for idx in top_indices]
            relevance_scores = [similarities[i][idx] for idx in top_indices]
            
            qa_results.append({
                "question": question,
                "relevant_documents": relevant_docs,
                "relevance_scores": relevance_scores
            })
        
        duration = time.time() - start_time
        
        return UseCaseResult(
            use_case="rag_system",
            success=True,
            performance_metrics={
                "processing_time": duration,
                "questions_processed": len(questions),
                "knowledge_base_size": len(knowledge_base),
                "average_relevance": sum(max(r["relevance_scores"]) for r in qa_results) / len(qa_results)
            },
            business_value="Enables intelligent document search, improves decision making, reduces manual research time",
            implementation_complexity="Very High",
            recommendations=[
                "Integrate with LLM for answer generation",
                "Implement conversation memory",
                "Add source citation capabilities"
            ]
        )
    
    def _print_use_case_result(self, result: UseCaseResult):
        """Print formatted use case result."""
        print(f"\n📊 {result.use_case.replace('_', ' ').title()}")
        print(f"   Success: {'✅' if result.success else '❌'}")
        print(f"   Business Value: {result.business_value}")
        print(f"   Implementation Complexity: {result.implementation_complexity}")
        
        if result.performance_metrics:
            print("   Performance Metrics:")
            for key, value in result.performance_metrics.items():
                print(f"     {key}: {value}")
        
        if result.recommendations:
            print("   Recommendations:")
            for rec in result.recommendations:
                print(f"     • {rec}")
    
    def generate_use_case_report(self, results: List[UseCaseResult]) -> str:
        """Generate comprehensive use case report."""
        report = []
        report.append("# EmbeddingGemma Use Cases for CoupaDownloads")
        report.append("=" * 60)
        report.append("")
        
        # Summary
        successful_cases = [r for r in results if r.success]
        report.append(f"## Summary")
        report.append(f"- Total Use Cases: {len(results)}")
        report.append(f"- Successful Demonstrations: {len(successful_cases)}")
        report.append(f"- Success Rate: {len(successful_cases)/len(results)*100:.1f}%")
        report.append("")
        
        # Individual use cases
        for result in results:
            report.append(f"## {result.use_case.replace('_', ' ').title()}")
            report.append(f"**Status:** {'✅ Success' if result.success else '❌ Failed'}")
            report.append(f"**Business Value:** {result.business_value}")
            report.append(f"**Implementation Complexity:** {result.implementation_complexity}")
            report.append("")
            
            if result.performance_metrics:
                report.append("### Performance Metrics")
                for key, value in result.performance_metrics.items():
                    report.append(f"- {key}: {value}")
                report.append("")
            
            if result.recommendations:
                report.append("### Recommendations")
                for rec in result.recommendations:
                    report.append(f"- {rec}")
                report.append("")
        
        # Overall recommendations
        report.append("## Overall Recommendations")
        report.append("")
        
        if len(successful_cases) >= 4:
            report.append("✅ **High Integration Potential**")
            report.append("- Multiple use cases demonstrated successfully")
            report.append("- Strong business value across different scenarios")
            report.append("- Consider phased implementation approach")
        elif len(successful_cases) >= 2:
            report.append("⚠️ **Moderate Integration Potential**")
            report.append("- Some use cases show promise")
            report.append("- Focus on high-value, low-complexity implementations")
            report.append("- Consider pilot program for selected use cases")
        else:
            report.append("❌ **Low Integration Potential**")
            report.append("- Limited successful demonstrations")
            report.append("- Consider alternative solutions")
            report.append("- Re-evaluate after addressing technical issues")
        
        return "\n".join(report)


def main():
    """Run use case demonstrations."""
    print("🎯 EmbeddingGemma Use Cases for CoupaDownloads")
    print("=" * 60)
    
    use_cases = CoupaDownloadsUseCases()
    results = use_cases.demonstrate_all_use_cases()
    
    # Generate report
    report = use_cases.generate_use_case_report(results)
    
    # Save report
    output_file = Path("reports") / f"use_cases_report_{time.strftime('%Y%m%d_%H%M%S')}.md"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"\n📊 Use case report saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()

