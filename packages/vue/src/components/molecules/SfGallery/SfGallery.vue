<template>
  <div class="sf-gallery">
    <div class="sf-gallery__stage">
      <div ref="glide" class="glide">
        <div class="glide__track" data-glide-el="track">
          <ul class="glide__slides">
            <li
              v-for="(picture, index) in images"
              :key="'slide-' + index"
              class="glide__slide"
              @mouseover="startZoom(picture)"
              @mousemove="moveZoom($event, index)"
              @mouseout="removeZoom(index)"
            >
              <SfImage
                ref="sfGalleryBigImage"
                class="sf-gallery__big-image"
                :class="{ 'sf-gallery__big-image--has-zoom': enableZoom }"
                :src="picture.desktop.url"
                :alt="picture.alt"
                :width="imageWidth"
                :height="imageHeight"
                @click="$emit('click:stage', { picture, index })"
              />
            </li>
          </ul>
        </div>
      </div>
      <transition name="sf-fade">
        <div
          ref="outSide"
          :class="{
            'display-none':
              !outsideZoom || !pictureSelected || (!outsideZoom && !enableZoom),
          }"
          :style="{ width: `${imageWidth}px`, height: `${imageHeight}px` }"
        >
          <SfImage
            ref="imgZoom"
            class="sf-gallery__zoom"
            :src="pictureSelectedUrl"
            :width="imageWidth"
            :height="imageHeight"
            :lazy="false"
            :alt="pictureSelected.alt"
          />
        </div>
      </transition>
    </div>
    <div class="sf-gallery__thumbs">
      <slot name="thumbs" v-bind="{ images, active: activeIndex, go }">
        <SfButton
          v-for="(image, index) in images"
          :key="'img-' + index"
          class="sf-button--pure sf-gallery__item"
          :class="{ 'sf-gallery__item--selected': index === activeIndex }"
          :aria-label="'Image ' + index"
          @click="go(index)"
        >
          <SfImage
            class="sf-gallery__thumb"
            :src="image.mobile.url"
            :alt="image.alt"
            :width="thumbWidth"
            :height="thumbHeight"
          />
        </SfButton>
      </slot>
    </div>
  </div>
</template>
<script>
import Glide from "@glidejs/glide";
import SfImage from "../../atoms/SfImage/SfImage.vue";
import SfButton from "../../atoms/SfButton/SfButton.vue";
export default {
  name: "SfGallery",
  components: {
    SfImage,
    SfButton,
  },
  props: {
    images: {
      type: Array,
      default: () => [],
    },
    imageWidth: {
      type: Number,
      default: 422,
    },
    imageHeight: {
      type: Number,
      default: 664,
    },
    thumbWidth: {
      type: [Number, String],
      default: 160,
    },
    thumbHeight: {
      type: [Number, String],
      default: 160,
    },
    current: {
      type: Number,
      default: 1,
    },
    sliderOptions: {
      type: Object,
      default() {
        return {
          type: "slider",
          autoplay: false,
          rewind: false,
          gap: 0,
        };
      },
    },
    outsideZoom: {
      type: Boolean,
      default: false,
    },
    enableZoom: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      positionStatic: {},
      eventHover: {},
      pictureSelected: { alt: "" },
      glide: null,
      activeIndex: this.current - 1,
      style: "",
    };
  },
  computed: {
    mapPictures() {
      // map images to handle picture tags with SfImage
      return this.images.map(({ desktop, big }) => ({
        mobile: desktop,
        desktop: big,
      }));
    },
    updatedSliderOptions() {
      return { ...this.sliderOptions, startAt: this.activeIndex };
    },
    pictureSelectedUrl() {
      const { zoom, big, desktop } = this.pictureSelected;
      const definedPicture = zoom || big || desktop;
      return definedPicture ? definedPicture.url : "";
    },
  },
  mounted() {
    this.$nextTick(() => {
      // handle slider with swipe and transitions with Glide.js
      // https://glidejs.com/docs/
      if (this.images.length < 1) return;
      const glide = new Glide(this.$refs.glide, this.updatedSliderOptions);
      glide.on("run", () => {
        this.go(glide.index);
      });
      glide.mount();
      this.glide = glide;
    });
  },
  updated() {
    if (this.glide) {
      this.$nextTick(() => {
        this.glide.mount();
      });      
    }    
  },
  beforeDestroy() {
    if (this.glide) {
      this.glide.destroy();
    }
  },
  methods: {
    positionObject(index) {
      if (this.$refs.sfGalleryBigImage) {
        if (this.outsideZoom) {
          return this.$refs.glide.getBoundingClientRect();
        } else {
          return this.$refs.sfGalleryBigImage[
            index
          ].$el.getBoundingClientRect();
        }
      }
      return "";
    },
    go(index) {
      if (!this.glide) return;
      this.activeIndex = index;
      /**
       * Event for current image change (`v-model`)
       * @type {Event}
       */
      this.$emit("click", index + 1);
      if (this.glide) {
        this.glide.go(`=${index}`);
      }
    },
    startZoom(picture) {
      if (this.enableZoom) {
        this.pictureSelected = picture;
      }
    },
    moveZoom($event, index) {
      if (this.enableZoom) {
        this.eventHover = $event;
        if (this.outsideZoom) {
          this.positionStatic = this.positionObject(index);
          this.$refs.imgZoom.$el.children[0].style.cssText =
            "top: 0; transform: scale(2);";
          this.$refs.imgZoom.$el.children[0].style.transformOrigin = `${
            $event.clientX - this.positionStatic.x
          }px ${$event.clientY - this.positionStatic.y}px`;
        } else {
          this.positionStatic = this.positionObject(index);
          this.$refs.sfGalleryBigImage[index].$el.children[0].style.cssText =
            "top: 0; transform: scale(2);";
          this.$refs.sfGalleryBigImage[
            index
          ].$el.children[0].style.transformOrigin = `${
            $event.clientX - this.positionStatic.x
          }px ${$event.clientY - this.positionStatic.y}px`;
        }
      }
    },
    removeZoom(index) {
      if (this.enableZoom) {
        this.pictureSelected = "";
        if (this.outsideZoom) return;
        this.$refs.sfGalleryBigImage[index].$el.children[0].style.transform =
          "scale(1)";
      }
    },
  },
};
</script>
<style lang="scss">
@import "~@storefront-ui/shared/styles/components/molecules/SfGallery.scss";
</style>
