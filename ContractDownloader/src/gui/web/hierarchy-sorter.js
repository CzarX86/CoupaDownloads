/*
 * HierarchySorter
 *
 * Thin application adapter around SortableJS. It owns the lifecycle of one
 * sortable list and provides button-based reordering for keyboard users.
 * Supplier and PO are deliberately rendered outside this container, so they
 * cannot be crossed by either interaction mode.
 */
(function attachHierarchySorter(global) {
    "use strict";

    class HierarchySorter {
        constructor(container, options = {}) {
            if (!container) throw new TypeError("HierarchySorter requires a container element.");

            this.container = container;
            this.onChange = typeof options.onChange === "function" ? options.onChange : () => {};
            this.disabled = Boolean(options.disabled);
            this.sortable = null;
            this.handleClick = this.handleClick.bind(this);
            this.container.addEventListener("click", this.handleClick);

            if (global.Sortable) {
                this.sortable = global.Sortable.create(this.container, {
                    animation: 150,
                    direction: "vertical",
                    draggable: "> li[data-column]",
                    handle: ".drag-handle",
                    filter: ".hierarchy-move, .hierarchy-toggle",
                    preventOnFilter: false,
                    forceFallback: true,
                    fallbackOnBody: true,
                    fallbackTolerance: 4,
                    supportPointer: false,
                    scroll: true,
                    scrollSensitivity: 50,
                    scrollSpeed: 12,
                    ghostClass: "hierarchy-ghost",
                    chosenClass: "hierarchy-chosen",
                    dragClass: "hierarchy-dragging",
                    fallbackClass: "hierarchy-drag-fallback",
                    onEnd: () => this.commit("drag"),
                });
            }

            this.setDisabled(this.disabled);
        }

        getOrder() {
            return [...this.container.querySelectorAll(":scope > li[data-column]")]
                .map((item) => item.dataset.column);
        }

        setDisabled(disabled) {
            this.disabled = Boolean(disabled);
            if (this.sortable) this.sortable.option("disabled", this.disabled);
            this.refreshControls();
        }

        refreshControls() {
            const items = [...this.container.querySelectorAll(":scope > li[data-column]")];
            items.forEach((item, index) => {
                const up = item.querySelector('[data-move-direction="up"]');
                const down = item.querySelector('[data-move-direction="down"]');
                const handle = item.querySelector(".drag-handle");
                if (up) up.disabled = this.disabled || index === 0;
                if (down) down.disabled = this.disabled || index === items.length - 1;
                if (handle) handle.disabled = this.disabled || items.length < 2 || !this.sortable;
            });
        }

        handleClick(event) {
            const button = event.target.closest("[data-move-direction]");
            if (!button || this.disabled || !this.container.contains(button)) return;

            const item = button.closest("li[data-column]");
            if (!item) return;
            const direction = button.dataset.moveDirection;
            if (direction === "up" && item.previousElementSibling) {
                item.previousElementSibling.before(item);
            } else if (direction === "down" && item.nextElementSibling) {
                item.nextElementSibling.after(item);
            } else {
                return;
            }
            this.commit("button");
        }

        commit(source) {
            this.refreshControls();
            this.onChange(this.getOrder(), source);
        }

        destroy() {
            this.container.removeEventListener("click", this.handleClick);
            if (this.sortable) this.sortable.destroy();
            this.sortable = null;
        }
    }

    global.HierarchySorter = HierarchySorter;
})(window);
