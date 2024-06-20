<script setup lang="ts">
import { ref, onMounted  } from "vue";

const emits = defineEmits(['infinite-scroll']);

const infiniteScroller = ref<HTMLTableElement | null>(null);
const endOfTable = ref<HTMLDivElement | null>(null);


onMounted(() => {
  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      emits('infinite-scroll');
      console.log('Intersecting');
    }

  },
  {
    root: infiniteScroller.value,
    rootMargin: '100px',


  });
  observer.observe(endOfTable.value as Element);
});

</script>
<template>
<div ref="infiniteScroller" class="card rounded max-h-[90vh] max-w-[75vw] overflow-auto customScroll">
  <slot></slot>
  <div ref="endOfTable"></div>
</div>
</template>
<style scoped>
@supports selector(::-webkit-scrollbar) {
  .customScroll::-webkit-scrollbar{
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
    background-color: #00A6BF;
  }

  .customScroll::-webkit-scrollbar-track {
    background-color: #9CA3AF;
    width: 5px;
  }
}
</style>
