<template>
  <div
    class="sf-input"
    :class="{
      'sf-input--has-text': !!value,
      'sf-input--invalid': !valid,
    }"
  >
    <div class="sf-input__wrapper">
      <label class="sf-input__label" :for="inputId" v-if="label">
        <!-- @slot Custom input label -->
        <slot name="label" v-bind="{ label }">{{ label }}</slot>
      </label>
      <input
        v-bind="inputAttributes"
        v-focus
        :value="value"
        :required="required"
        :disabled="disabled"
        :name="name"
        :class="{ 'sf-input--is-password': isPassword }"
        :type="inputType"
        v-on="listeners"
      />
      <span class="sf-input__bar" aria-hidden></span>
      <slot
        v-if="isPassword"
        v-bind="{
          isPasswordVisible,
          switchVisibilityPassword,
        }"
        name="show-password"
      >
        <SfButton
          class="sf-input__password-button"
          type="button"
          aria-label="switch-visibility-password"
          :aria-pressed="isPasswordVisible.toString()"
          @click="switchVisibilityPassword"
        >
          <SfIcon
            class="sf-input__password-icon"
            :class="{
              'sf-input__password-icon--hidden': !isPasswordVisible,
            }"
            icon="show_password"
            size="1.5rem"
          ></SfIcon>
        </SfButton>
      </slot>
    </div>
    <div
      :id="errorMessageId"
      aria-live="polite"
      class="sf-input__error-message"
    >
      <transition name="fade">
        <!-- @slot Custom error message of form input -->
        <slot v-if="!valid" name="error-message" v-bind="{ errorMessage }">
          <div>{{ errorMessage }}</div>
        </slot>
      </transition>
    </div>
  </div>
</template>
<script>
import SfIcon from "../../atoms/SfIcon/SfIcon.vue";
import SfButton from "../../atoms/SfButton/SfButton.vue";
import { focus } from "../../../utilities/directives";
export default {
  name: "SfInput",
  directives: {
    focus,
  },
  components: { SfIcon, SfButton },
  inheritAttrs: false,
  props: {
    /**
     * Current input value (`v-model`)
     */
    value: {
      type: [String, Number],
      default: null,
    },
    /**
     * Form input label
     */
    label: {
      type: String,
      default: null,
    },
    /**
     * Form input name
     */
    name: {
      type: String,
      default: null,
    },
    /**
     * Form input type
     */
    type: {
      type: String,
      default: "text",
    },
    /**
     * Validate value of form input
     */
    valid: {
      type: Boolean,
      default: true,
    },
    /**
     * Error message value of form input. It will be appeared if `valid` is `true`.
     */
    errorMessage: {
      type: String,
      default: null,
    },
    /**
     * Native input required attribute
     */
    required: {
      type: Boolean,
      default: false,
      description: "Native input required attribute",
    },
    /**
     * Native input disabled attribute
     */
    disabled: {
      type: Boolean,
      default: false,
      description: "Native input disabled attribute",
    },
    /**
     * Status of show password icon display
     */
    hasShowPassword: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      isPasswordVisible: false,
      inputType: "",
      isNumberTypeSafari: false,
    };
  },
  computed: {
    inputId() {
      return this.$attrs.id || this.name || `sf-input-${this._uid}`;
    },
    errorMessageId() {
      return `${this.inputId}-error-message`;
    },
    describedByIds() {
      const ids = (this.$attrs["aria-describedby"] || "")
        .split(" ")
        .filter(Boolean);

      if (!this.valid) {
        ids.push(this.errorMessageId);
      }

      return ids.filter((id, index) => ids.indexOf(id) === index).join(" ") || undefined;
    },
    inputAttributes() {
      const attributes = { ...this.$attrs };

      delete attributes.id;
      delete attributes["aria-describedby"];
      delete attributes["aria-invalid"];

      return {
        ...attributes,
        id: this.inputId,
        "aria-describedby": this.describedByIds,
        "aria-invalid": (!this.valid).toString(),
      };
    },
    listeners() {
      return {
        ...this.$listeners,
        input: (event) => this.$emit("input", event.target.value),
      };
    },
    isPassword() {
      return this.type === "password" && this.hasShowPassword;
    },
  },
  watch: {
    type: {
      immediate: true,
      handler: function (type) {
        let inputType = type;
        // Safari has bug for number input
        if (typeof window !== "undefined" || typeof document !== "undefined") {
          const ua = navigator.userAgent.toLocaleLowerCase();
          if (
            ua.indexOf("safari") !== -1 &&
            ua.indexOf("chrome") === -1 &&
            type === "number"
          ) {
            this.isNumberTypeSafari = true;
            inputType = "text";
          }
        }
        this.inputType = inputType;
      },
    },
    value: {
      immediate: true,
      handler: function (value) {
        if (!this.isNumberTypeSafari) return;
        if (isNaN(value)) {
          this.$emit("input");
        }
      },
    },
  },
  methods: {
    switchVisibilityPassword() {
      this.isPasswordVisible = !this.isPasswordVisible;
      this.inputType = this.isPasswordVisible ? "text" : "password";
    },
  },
};
</script>
<style lang="scss">
@import "~@storefront-ui/shared/styles/components/atoms/SfInput.scss";
</style>
