<template>
  <div class="node-list-container">
    <div v-for="(item, idx) in visibleItems" :key="idx + item.uid">
      <slot v-bind:item="item"></slot>
    </div>
    <div v-if="numRemaining">
      <p class="text-center">({{ numRemaining }} more)</p>
    </div>
  </div>
</template>

<style scoped>
.node-list-container {
  display: grid;
  grid-gap: 1rem;
}

@media (min-width: 1200px) {
  .node-list-container {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

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
