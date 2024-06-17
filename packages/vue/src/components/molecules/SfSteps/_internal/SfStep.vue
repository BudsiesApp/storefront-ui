<template>
  <div class="sf-step">
    <slot
      v-if="active || useVShow"
      v-show="active || !useVShow"
      :index="index"
    ></slot>
  </div>
</template>
<script>
export default {
  name: "SfStep",
  inject: ["stepsData"],
  props: {
    /**
     * Name of the step
     */
    name: {
      type: String,
      default: "",
    },
    /**
     * Use `v-show` instead `v-if` directive for hide inactive steps content
     */
    useVShow: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    internalName() {
      if (this.stepsData) {
        return this.stepsData.name;
      }
      return null;
    },
    index() {
      if (this.stepsData) {
        return this.stepsData.index;
      }
      return null;
    },
    active() {
      return this.internalName === this.name;
    },
  },
  mounted() {
    this.stepsData.updateSteps(this.name);
  },
};
</script>
