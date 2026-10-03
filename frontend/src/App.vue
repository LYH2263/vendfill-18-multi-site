<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useLocation } from './composables/useLocation'

const { loaded, locations, currentLocationId, setCurrentLocation, init } = useLocation()
onMounted(init)
</script>
<template>
  <div class="vf-cabinet">
    <div class="vf-cabinet-top">
      <span class="vf-logo">VendFill</span>
      <span class="vf-tag">售货机补货 · 机面操作台</span>
    </div>
    <div class="vf-body">
      <aside class="vf-site-rail">
        <div class="vf-rail-title">当前点位</div>
        <select
          class="vf-loc-select"
          :value="currentLocationId ?? ''"
          :disabled="!loaded || locations.length === 0"
          @change="setCurrentLocation(($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)"
        >
          <option value="" disabled>{{ loaded ? (locations.length ? '请选择点位' : '请先新建点位') : '加载中…' }}</option>
          <option v-for="l in locations" :key="l.id" :value="l.id">{{ l.code }} · {{ l.name }}</option>
        </select>
        <RouterLink to="/locations" class="vf-site-btn" style="font-size:0.7rem">管理点位 →</RouterLink>
        <div class="vf-rail-title" style="padding-top:0.6rem">机位列表</div>
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
