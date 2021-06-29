<template>
  <div>
    <div v-for="(item, idx) in visibleItems" :key="visibleItems.length + idx">
      <slot v-bind:item="item"></slot>
    </div>
    <div v-if="numRemaining">
      <p class="text-center">({{ numRemaining }} more)</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    items: Array,
  },
  data() {
    const visibleItems = this.items.slice(0, 10);
    return {
      visibleItems,
      keyNonce: "",
    };
  },
  computed: {
    numRemaining() {
      return this.items.length - this.visibleItems.length;
    },
  },
  watch: {
    items() {
      this.visibleItems = this.items.slice(0, 10);
      this.keyNonce = new Date().getTime();
    },
  },
  methods: {
    onScroll(event) {
      if (this.$el.getBoundingClientRect().bottom < window.innerHeight) {
        this.visibleItems = this.items.slice(0, this.visibleItems.length + 10);
      }
    },
  },
  mounted() {
    window.addEventListener("scroll", this.onScroll);
  },
  destroyed() {
    window.removeEventListener("scroll", this.onScroll);
  },
};
</script>
