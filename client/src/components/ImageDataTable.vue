<script setup lang="ts">
const props = defineProps({
    imageData:{
    type: Object,
    required: true
    }
})

const sortedData = Object.entries(props.imageData).sort(([keyA], [keyB]) => {
    if (keyA === 'missing_tags') {
        return -1;
    } else if (keyB === 'missing_tags') {
        return 1;
    } else {
        return 0;
    }
});
</script>

<template>
    <table class="table table-auto table-xs w-full">
        <thead>
            <tr>
                <th v-for="tag in sortedData" :key="tag[0]">
                    {{ tag[0] }}
                </th>

            </tr>
        </thead>
        <tbody>
            <tr>
                <template v-for="rule in sortedData" :key="rule[0]">
                    <td
                    v-if="rule[0] === 'missing_tags'"
                    >
                        <span v-for="(tag, id) in rule[1][0]" :key="id">
                            {{ id }} : {{ tag }}
                        </span>
                </td>
                    <td
                    v-else
                    >
                        {{ rule[1] }}
                    </td>
            </template>
            </tr>
        </tbody>
    </table>
</template>
