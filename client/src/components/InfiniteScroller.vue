<script setup lang="ts">
import { ref, onMounted } from "vue";

const emits = defineEmits(["infinite-scroll"]);

const infiniteScroller = ref<HTMLTableElement | null>(null);
const endOfTable = ref<HTMLDivElement | null>(null);

onMounted(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting) {
        emits("infinite-scroll");
      }
    },
    {
      root: infiniteScroller.value,
      rootMargin: "200px",
    },
  );
  observer.observe(endOfTable.value as Element);
});
</script>
<template>
  <div
    ref="infiniteScroller"
    class="card rounded max-h-[calc(100vh-50px)] max-w-[calc(100vw-425px)] overflow-auto customScroll"
  >
    <slot />
    <div ref="endOfTable" />
  </div>
</template>
<style scoped>
@supports selector(::-webkit-scrollbar) {
  .customScroll::-webkit-scrollbar {
    width: 10px;
    height: 10px;
  }

  .customScroll::-webkit-scrollbar-button,
  .customScroll::-webkit-scrollbar-corner {
    display: none;
  }

  .customScroll::-webkit-scrollbar-thumb,
  .customScroll::-webkit-scrollbar-track {
    border-radius: 20px;
  }

  .customScroll::-webkit-scrollbar-thumb {
    background-color: #00a6bf;
  }

  .customScroll::-webkit-scrollbar-track {
    background-color: #6b7280;
    width: 5px;
  }
}
</style>
