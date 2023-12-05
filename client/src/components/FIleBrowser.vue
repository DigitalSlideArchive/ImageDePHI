<script lang="ts">
// TODO
// props:modal, input/output
// directory call

</script>
<template>
    <!-- <div class="modal {{ 'modal-open' if modal==current_modal }}"
     id="{{ modal }}"> -->
  <div class="w-full max-w-4xl h-4/5 rounded-xl overflow-hidden">
    <div class="modal-box w-full max-w-4xl h-full overflow-auto pt-0">
      <div class="sticky top-0 pt-6 bg-white">
        <div class="flex justify-between">
          <h2 class="text-lg font-semibold">
            <!-- {% block selector_title required %}
            {% endblock selector_title %} -->
          </h2>
          <!-- <a href="{%- block selected_url scoped -%}{%- endblock selected_url -%}"> -->
            <button class="btn bg-primary float-right" type="button">Select</button>
          <!-- </a> -->
        </div>
        <div class="text-sm breadcrumbs mb-4 border-b-2">
          <ul class="flex flex-wrap">
            <!-- {% for ancestor in directory_data.ancestors %}
              <li class="mr-1 text-base">
                {# The root directory has an empty string "name" #}
                {% set ancestor_name = ancestor.name|default('/', true) %}
                {% if loop.last %}
                  <span class="font-black">{{ ancestor_name }}</span>
                {% else %}
                  <a class="text-blue-700"
                     href="{%- block selector_ancestor_url scoped required -%}{%- endblock selector_ancestor_url -%}">
                    {{ ancestor_name }}
                  </a>
                {% endif %}
              </li>
            {% endfor %} -->
          </ul>
        </div>
      </div>
      <ul>
        <!-- {% for child_directory in directory_data.child_directories|sort %}
          {# Put the <a> outside, to make the whole line clickable #} -->
          <!-- <a href="{%- block selector_child_directory_url scoped required -%}{%- endblock selector_child_directory_url -%}"> -->
            <li class="hover:bg-base-300">
              <i class="ri-folder-3-fill text-neutral"></i>
              <!-- {{ child_directory.name }} -->
            </li>
          <!-- </a> -->
        <!-- {% endfor %} -->
      </ul>
      <ul class="pl-2">
        <!-- {% for child_image in directory_data.child_images[:10] %} -->
          <li>
            <i class="ri-image-fill text-sky-800"></i>
            <!-- {{ child_image.name }} -->
          </li>
        <!-- {% endfor %}
        {% if directory_data.child_images|length > 10 %}
          <li class="italic">{{ directory_data.child_images|length - 10 }} More Images</li>
        {% endif %} -->
      </ul>
    </div>
  </div>
<!-- </div> -->

</template>
