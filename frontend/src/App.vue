<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { current, loadLocations, locations, switchLocation } from './store'

onMounted(loadLocations)
</script>
<template>
  <div class="vf-cabinet">
    <div class="vf-cabinet-top">
      <span class="vf-logo">VendFill</span>
      <span class="vf-tag">售货机补货 · 机面操作台</span>
      <span class="vf-tag" v-if="current">当前点位：{{ current.code }} · {{ current.name }}</span>
    </div>
    <div class="vf-body">
      <aside class="vf-site-rail">
        <div class="vf-rail-title">机位列表</div>
        <button
          v-for="loc in locations"
          :key="loc.id"
          class="vf-site-btn vf-loc-btn"
          :class="{ 'vf-loc-active': current?.id === loc.id }"
          @click="switchLocation(loc.id)"
        >
          {{ loc.code }}
        </button>
        <div class="vf-rail-title" style="margin-top:0.6rem">功能</div>
        <RouterLink to="/locations" class="vf-site-btn">点位</RouterLink>
        <RouterLink to="/lanes" class="vf-site-btn">货道格子</RouterLink>
        <RouterLink to="/sales" class="vf-site-btn">销量</RouterLink>
        <RouterLink to="/refills" class="vf-site-btn">补货小票</RouterLink>
        <RouterLink to="/full" class="vf-site-btn">满仓</RouterLink>
        <RouterLink to="/summary" class="vf-site-btn">汇总</RouterLink>
      </aside>
      <section class="vf-glass">
        <RouterView />
      </section>
    </div>
  </div>
</template>
