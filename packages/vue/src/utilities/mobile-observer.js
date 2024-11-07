import Vue from "vue";
let observer;
const isMobileMax = 1023;
export const onMediaMatch = (e) => {
  observer.isMobile = e.matches;
};
export const setupListener = () => {
  if (
    typeof window === "undefined" ||
    typeof document === "undefined" ||
    !window.matchMedia
  ) {
    return;
  }
  observer.isMobile =
    Math.max(document.documentElement.clientWidth, window.innerWidth) <=
    isMobileMax;
  window.matchMedia(`(max-width: ${isMobileMax}px)`).addListener(onMediaMatch);
  observer.isInitialized = true;
};
export const tearDownListener = () => {
  if (
    typeof window !== "undefined" &&
    typeof document !== "undefined" &&
    window.matchMedia
  ) {
    window
      .matchMedia(`(max-width: ${isMobileMax}px)`)
      .removeListener(onMediaMatch);
  }
};
export const mapMobileObserver = () => {
  if (!observer) {
    observer = Vue.observable({
      isMobile: false,
      clients: 0,
      isInitialized: false,
    });
  }

  return {
    isMobile: {
      get() {
        if (observer && !observer.isInitialized) {
          setupListener();
        }
        return observer ? observer.isMobile : false;
      },
    },
    mobileObserverClients: {
      get() {
        return observer ? observer.clients : 0;
      },
    },
    mobileObserverIsInitialized: {
      get() {
        return observer ? observer.isInitialized : false;
      },
    },
  };
};
export const unMapMobileObserver = () => {
  // TODO: destroy observer when observer initialization will be fixed
};
