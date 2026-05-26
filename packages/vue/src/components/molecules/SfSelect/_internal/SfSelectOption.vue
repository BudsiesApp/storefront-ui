<template>
  <li
    :id="myOptionId"
    role="option"
    class="sf-select-option"
    :class="{ 'sf-select-option--is-active': isActiveOption }"
    :aria-selected="isSelected ? 'true' : 'false'"
    @click.stop="clicked"
  >
    <!-- @slot -->
    <slot />
  </li>
</template>
<script>
import { focus } from "../../../../utilities/directives";
export default {
  name: "SfSelectOption",
  directives: { focus },
  props: {
    value: {
      type: [String, Number, Object],
      default: "",
    },
  },
  computed: {
    myIndex() {
      return this.$parent.indexes[JSON.stringify(this.value)];
    },
    myOptionId() {
      return this.$parent.optionId(this.myIndex);
    },
    isSelected() {
      return this.myIndex === this.$parent.index;
    },
    isActiveOption() {
      return this.myIndex === this.$parent.activeIndex;
    },
  },
  methods: {
    clicked() {
      this.$parent.$emit("update", this.myIndex);
    },
  },
};
</script>
