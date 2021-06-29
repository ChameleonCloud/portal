<template>
  <div>
    <nav class="btn-toolbar" role="toolbar">
      <div class="btn-group mr-2" role="group" aria-label="Prev">
        <button type="button" class="btn" v-on:click="prevPage()">Prev</button>
      </div>
      <div class="btn-group mr-2" role="group" aria-label="Pages">
        <button
          v-for="page in totalPages"
          :key="page"
          class="btn btn-secondary"
          :class="{
            'btn-info': page - 1 === currentPage,
          }"
          v-on:click="gotoPage(page - 1)"
        >
          {{ page }}
        </button>
      </div>
      <div class="btn-group" role="group" aria-label="Next">
        <button type="button" class="btn" v-on:click="nextPage()">Next</button>
      </div>
    </nav>
    <div v-for="(item, idx) in pagedItems" :key="idx + items.length">
      <slot v-bind:item="item"></slot>
    </div>
  </div>
</template>

<script>
function getPageOfItems(items, currentPage, perPage) {
  const start = perPage * currentPage;
  return items.slice(start, start + perPage);
}

function getTotalPages(items, perPage) {
  const numItems = items.length;
  return Math.floor(numItems / perPage) + (numItems % perPage > 0 ? 1 : 0);
}

export default {
  props: {
    perPage: { type: Number, default: 10 },
    items: Array,
  },
  data() {
    return {
      currentPage: 0,
      totalPages: getTotalPages(this.items),
      pagedItems: getPageOfItems(this.items, 0, this.perPage),
    };
  },
  watch: {
    items() {
      this.currentPage = 0;
      this.totalPages = getTotalPages(this.items, this.perPage);
      this.pagedItems = getPageOfItems(
        this.items,
        this.currentPage,
        this.perPage
      );
    },
  },
  methods: {
    prevPage() {
      this.gotoPage(this.currentPage - 1);
    },
    nextPage() {
      this.gotoPage(this.currentPage + 1);
    },
    gotoPage(page) {
      this.currentPage = Math.min(this.totalPages - 1, Math.max(0, page));
      this.pagedItems = getPageOfItems(
        this.items,
        this.currentPage,
        this.perPage
      );
    },
  },
};
</script>
