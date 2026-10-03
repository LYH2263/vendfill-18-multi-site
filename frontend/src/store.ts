import { ref } from 'vue'
import { api } from './api'

export interface Location {
  id: number
  code: string
  name: string
  address: string
}

/** 全部点位（仅点位管理页可见全部；五处业务页只服务 current） */
export const locations = ref<Location[]>([])
/** 当前点位 —— 货道/销量/补货单/满仓/汇总五页的作用域 */
export const current = ref<Location | null>(null)
/** 切换当前点位后自增，驱动各页重载 */
export const dataVersion = ref(0)

export async function loadLocations(): Promise<void> {
  locations.value = await api<Location[]>('/locations')
  try {
    current.value = await api<Location>('/locations/current')
  } catch {
    current.value = null
  }
}

export async function switchLocation(id: number): Promise<void> {
  if (current.value?.id === id) return
  current.value = await api<Location>('/locations/current', {
    method: 'PUT',
    body: JSON.stringify({ location_id: id }),
  })
  dataVersion.value++
}
