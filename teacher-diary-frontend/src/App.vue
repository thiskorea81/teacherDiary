<template>
  <div>
    <NavBar />
    <main style="max-width: 1000px; margin: 24px auto; padding: 0 16px;">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import NavBar from "@/components/NavBar.vue";
</script>

<style>
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
a { text-decoration: none; color: inherit; }
nav a.router-link-active { font-weight: 700; }
label { display:block; margin: 8px 0 4px; }
input, select, button, textarea {
  font: inherit; padding: 8px; border: 1px solid #ccc; border-radius: 8px;
}
button { cursor: pointer; }
.table { width:100%; border-collapse: collapse; }
.table th, .table td { border-bottom: 1px solid #eee; padding: 8px; }
.badge { padding: 2px 8px; border-radius: 999px; background:#eee; font-size: 12px; }
</style>
