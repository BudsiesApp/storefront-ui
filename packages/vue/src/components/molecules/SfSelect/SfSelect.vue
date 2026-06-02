<template>
  <div
    v-click-outside="closeHandler"
    :class="{
      'sf-select--is-active': isActive,
      'sf-select--is-selected': isSelected,
      'sf-select--is-required': required,
      'sf-select--is-disabled': disabled,
      'sf-select--is-flipped': isFlipped
    }"
    class="sf-select"
    @click="toggle($event)"
  >
    <div style="position: relative;">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div
        :id="triggerId"
        v-focus
        tabindex="0"
        role="combobox"
        aria-haspopup="listbox"
        :aria-expanded="open.toString()"
        :aria-controls="listboxId"
        :aria-activedescendant="open && activeIndex >= 0 ? optionId(activeIndex) : undefined"
        :aria-describedby="describedByIds"
        :aria-invalid="valid === undefined ? undefined : (!valid).toString()"
        :aria-labelledby="resolvedLabelId"
        class="sf-select__selected sf-select-option"
        v-html="html"
        @keydown.up.prevent="move(-1)"
        @keydown.down.prevent="move(1)"
        @keydown.home.prevent="moveToFirst"
        @keydown.end.prevent="moveToLast"
        @keydown.enter.prevent="enter"
        @keydown.space.prevent="enter"
        @keydown.esc.prevent="closeHandler"
        @keydown.tab="closeHandler"
      ></div>
      <slot name="label">
        <div v-if="label" :id="internalLabelId" class="sf-select__label">
          {{ label }}
        </div>
      </slot>
      <slot name="icon">
        <SfChevron class="sf-select__chevron" />
      </slot>

      <transition name="sf-select">
        <div
          v-show="open"
          class="sf-select__dropdown"
        >
          <!--  sf-select__option -->
          <ul
            :id="listboxId"
            ref="scrollableList"
            role="listbox"
            :style="{ maxHeight }"
            class="sf-select__options"
          >
            <slot />
          </ul>
          <slot name="cancel">
          </slot>
        </div>
      </transition>
    </div>
    <div
      :id="errorMessageId"
      aria-live="polite"
      class="sf-select__error-message"
    >
      <transition name="fade">
        <!-- @slot Custom error message of form select -->
        <slot v-if="!valid" name="error-message" v-bind="{ errorMessage }">
          <div>{{ errorMessage }}</div>
        </slot>
      </transition>
    </div>
  </div>
</template>
<script>
import Vue from "vue";
import {
  disableBodyScroll,
  enableBodyScroll,
  clearAllBodyScrollLocks,
} from "body-scroll-lock";

import SfSelectOption from "./_internal/SfSelectOption.vue";
import SfChevron from "../../atoms/SfChevron/SfChevron.vue";
import SfButton from "../../atoms/SfButton/SfButton.vue";
import SfOverlay from "../../atoms/SfOverlay/SfOverlay.vue";
import { focus } from "../../../utilities/directives";
import { clickOutside } from "../../../utilities/directives";
import { mapMobileObserver, unMapMobileObserver } from '../../../utilities/mobile-observer';

Vue.component("SfSelectOption", SfSelectOption);

const maxAvailableHeightCoefficient = 0.6;

export default {
  name: "SfSelect",
  directives: { focus, clickOutside },
  components: {
    SfButton,
    SfChevron,
    SfOverlay,
  },
  model: {
    prop: "selected",
    event: "change",
  },
  props: {
    /**
     * Select field label
     */
    label: {
      type: String,
      default: "",
    },
    /**
     * Selected item value
     */
    selected: {
      type: [String, Number, Object],
      default: "",
    },
    /**
     * Dropdown list size
     */
    size: {
      type: Number,
      default: 5,
    },
    /**
     * Required attribute
     */
    required: {
      type: Boolean,
      default: false,
    },
    /**
     * Validate value of form input
     */
    valid: {
      type: Boolean,
      default: undefined,
    },
    /**
     * Disabled status of form select
     */
    disabled: {
      type: Boolean,
      default: false,
    },
    /**
     * Error message value of form select. It will be appeared if `valid` is `true`.
     */
    errorMessage: {
      type: String,
      default: "This field is not correct.",
    },
    /**
     * Id of an external label element for aria-labelledby
     */
    labelId: {
      type: String,
      default: "",
    },
    /**
     * Lock body scroll when dropdown is show
     */
    shouldLockScrollOnOpen: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      open: false,
      isFlipped: false,
      options: [],
      indexes: {},
      optionHeight: 0,
      maxAvailableHeight: 0,
      activeIndex: -1,
    };
  },
  computed: {
    ...mapMobileObserver(),
    triggerId() {
      return `sf-select-trigger-${this._uid}`;
    },
    errorMessageId() {
      return `${this.triggerId}-error-message`;
    },
    listboxId() {
      return `sf-select-listbox-${this._uid}`;
    },
    internalLabelId() {
      return `sf-select-label-${this._uid}`;
    },
    describedByIds() {
      if (this.valid !== false) {
        return undefined;
      }

      return this.errorMessageId;
    },
    resolvedLabelId() {
      return this.labelId || (this.label ? this.internalLabelId : undefined);
    },
    index() {
      const stringified = this.indexes[JSON.stringify(this.selected)];
      if (typeof stringified === "undefined") {
        return -1;
      }
      return stringified;
    },
    html() {
      if (this.index < 0) return;
      return this.options[this.index].html;
    },
    maxHeightValue() {
      if (!this.size) return;

      return Math.min(
        this.optionHeight * this.size,
        this.maxAvailableHeight
      );
    },
    maxHeight() {
      if (!this.maxHeightValue) return;

      return `${this.maxHeightValue}px`;
    },
    isActive() {
      return this.open;
    },
    isSelected() {
      return this.selected;
    },
  },
  watch: {
    open: {
      immediate: true,
      handler: function (visible) {
        if (visible) {
          const updateMaxAvailableHeightFunction = this.isMobile
            ? this.updateMaxAvailableHeightForMobile
            : this.updateMaxAvailableHeightForDesktop;

          this.$nextTick(() => {
            this.optionHeight = this.$slots.default[0].elm.offsetHeight;
            updateMaxAvailableHeightFunction();
          });
        }

        this.toggleBodyScrollLock();
      },
    },
    shouldLockScrollOnOpen: {
      immediate: true,
      handler: function () {
        this.toggleBodyScrollLock();
      },
    },
  },
  created: function () {},
  mounted: function () {
    this.addOptionsAndIndexes();
  },
  updated() {
    if (
      this.$slots.default &&
      this.$slots.default.length > this.options.length
    ) {
      this.addOptionsAndIndexes();
    }
  },
  beforeDestroy: function () {
    this.$off("update", this.update);
    this.enableBodyScroll();
    unMapMobileObserver();
  },
  methods: {
    optionId(index) {
      return `sf-select-option-${this._uid}-${index}`;
    },
    commitSelection(index) {
      if (index >= 0 && index < this.options.length) {
        this.$emit("change", this.options[index].value);
      }
    },
    openDropdown() {
      if (this.disabled) {
        return;
      }

      this.activeIndex = this.index >= 0 ? this.index : 0;
      this.open = true;
      this.$nextTick(() => this.scrollActiveOptionIntoView());
    },
    closeDropdown() {
      this.open = false;
      this.activeIndex = -1;
    },
    scrollActiveOptionIntoView() {
      if (this.activeIndex < 0) {
        return;
      }

      const list = this.$refs.scrollableList;

      if (!list) {
        return;
      }

      const option = list.children[this.activeIndex];

      if (!option) {
        return;
      }

      option.scrollIntoView({ block: "nearest" });
    },
    move(delta) {
      if (!this.open) {
        return;
      }

      let next = this.activeIndex + delta;

      if (next < 0) {
        next = 0;
      }

      if (next >= this.options.length) {
        next = this.options.length - 1;
      }

      this.activeIndex = next;
      this.scrollActiveOptionIntoView();
    },
    moveToFirst() {
      if (!this.open) {
        return;
      }

      this.activeIndex = 0;
      this.scrollActiveOptionIntoView();
    },
    moveToLast() {
      if (!this.open) {
        return;
      }

      this.activeIndex = this.options.length - 1;
      this.scrollActiveOptionIntoView();
    },
    enter() {
      if (!this.open) {
        this.openDropdown();
      } else {
        if (this.activeIndex >= 0) {
          this.commitSelection(this.activeIndex);
        }

        this.closeDropdown();
      }
    },
    updateMaxAvailableHeightForMobile() {
      const rect = this.$el.getBoundingClientRect();
      const bottomHeight = document.body.clientHeight - rect.bottom;

      this.maxAvailableHeight = Math.max(bottomHeight, rect.top);
      this.isFlipped = rect.top > bottomHeight && bottomHeight < this.maxHeightValue;
    },
    updateMaxAvailableHeightForDesktop() {
      this.maxAvailableHeight = document.body.clientHeight * maxAvailableHeightCoefficient;
    },
    update(index) {
      this.commitSelection(index);
      this.closeDropdown();
    },
    addOptionsAndIndexes() {
      const options = [];
      const indexes = {};

      if (!this.$slots.default) return;

      this.$on("update", this.update);
      this.$slots.default.forEach(({ tag, componentOptions, elm }, index) => {
        if (!tag) return;
        options.push({
          ...componentOptions.propsData,
          html: elm.innerHTML,
          id: this.optionId(index),
        });
        indexes[JSON.stringify(componentOptions.propsData.value)] = index;
      });

      this.options = options;
      this.indexes = indexes;
    },
    toggle(event) {
      if (
        (this.$refs.cancel &&
          event &&
          event.target.contains(this.$refs.cancel.$el)) ||
        this.disabled
      )
        return;
      if (this.open) {
        this.closeDropdown();
      } else {
        this.openDropdown();
      }
    },
    closeHandler() {
      this.closeDropdown();
    },
    enableBodyScroll() {
      const scrollableContainer = this.$refs["scrollableList"];

      if (!scrollableContainer) {
        clearAllBodyScrollLocks();
        return;
      }

      enableBodyScroll(scrollableContainer);
    },
    toggleBodyScrollLock() {
      const scrollableContainer = this.$refs["scrollableList"];

      if (!scrollableContainer) {
        return;
      }

      if (this.open && this.shouldLockScrollOnOpen) {
        disableBodyScroll(scrollableContainer);
      } else {
        enableBodyScroll(scrollableContainer);
      }
    },
  },
};
</script>
<style lang="scss">
@import "~@storefront-ui/shared/styles/components/molecules/SfSelect.scss";
</style>
