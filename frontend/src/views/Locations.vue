<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { current, loadLocations, locations, switchLocation } from '../store'

const error = ref('')
const notice = ref('')
const form = ref({ code: '', name: '', address: '' })

onMounted(loadLocations)

async function run(fn: () => Promise<void>) {
  error.value = ''
  notice.value = ''
  try { await fn() } catch (e: any) { error.value = e.message || String(e) }
}

async function create() {
  if (!form.value.code.trim() || !form.value.name.trim()) {
    error.value = '编码与名称必填'
    return
  }
  await run(async () => {
    await api('/locations', { method: 'POST', body: JSON.stringify(form.value) })
    form.value = { code: '', name: '', address: '' }
    notice.value = '点位已创建，可在左侧机位列表切换为当前点位'
    await loadLocations()
  })
}

async function activate(id: number) {
  await run(async () => {
    await switchLocation(id)
    notice.value = '已切换当前点位'
  })
}

async function remove(id: number, code: string) {
  await run(async () => {
    await api(`/locations/${id}`, { method: 'DELETE' })
    notice.value = `点位 ${code} 已删除`
    await loadLocations()
  })
}
</script>
<template>
  <h1>点位 / 机位</h1>
  <p class="sub">点位档案管理 · 新建点位后切换为当前点位即可维护其货道与单据</p>
  <div v-if="error" class="vf-error">{{ error }}</div>
  <div v-if="notice" class="vf-notice">{{ notice }}</div>
  <div class="card">
    <div class="vf-form">
      <input v-model="form.code" placeholder="编码，如 VM-02" style="width:130px" />
      <input v-model="form.name" placeholder="名称" style="width:180px" />
      <input v-model="form.address" placeholder="地址" style="flex:1;min-width:160px" />
      <button class="btn" @click="create">新建点位</button>
    </div>
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>地址</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="r in locations" :key="r.id">
          <td><strong style="color:var(--vf-led)">{{ r.code }}</strong></td>
          <td>{{ r.name }}</td>
          <td>{{ r.address }}</td>
          <td><span v-if="current?.id === r.id" class="badge badge-ok">当前点位</span></td>
          <td>
            <button
              v-if="current?.id !== r.id"
              class="btn btn-ghost btn-sm"
              @click="activate(r.id)"
            >设为当前</button>
            <button
              v-if="current?.id !== r.id"
              class="btn btn-danger btn-sm"
              style="margin-left:0.4rem"
              @click="remove(r.id, r.code)"
            >删除</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
