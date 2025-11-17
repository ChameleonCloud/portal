<template>
  <div class="node-list-container">
    <div
      v-for="(item, idx) in visibleItems"
      :key="idx + item.uid"
      :class="{ 'is-header': item.isHeader }"
    >
      <slot v-bind:item="item" v-bind:index="idx"></slot>
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

  .is-header {
    grid-column: 1 / -1;
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
    scrollToIndex(index) {
      if (index >= this.visibleItems.length) {
        this.visibleItems = this.items.slice(0, index + 10); // show 10 more for context
      }

      this.$nextTick(() => {
        // We need to find the right child element. The `v-for` renders a div wrapper.
        const element = this.$el.children[index];
        if (element) {
          element.scrollIntoView({ behavior: "auto" });
        }
      });
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
