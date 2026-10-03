import { computed, ref } from 'vue'
import { api } from '../api'
import type { LocationDTO } from '../types'

const STORAGE_KEY = 'vendfill:location_id'

// 模块级单例：所有页面共享同一份当前点位状态。
const locations = ref<LocationDTO[]>([])
const currentLocationId = ref<number | null>(
  Number(localStorage.getItem(STORAGE_KEY)) || null,
)
const loaded = ref(false)
const initError = ref('')

const currentLocation = computed(
  () => locations.value.find((l) => l.id === currentLocationId.value) ?? null,
)

async function init() {
  if (loaded.value) return
  try {
    const rows = await api<LocationDTO[]>('/locations')
    locations.value = rows
    const stillExists = rows.some((l) => l.id === currentLocationId.value)
    if (!stillExists) setCurrentLocation(rows[0]?.id ?? null)
  } catch (e: any) {
    initError.value = e?.message || '点位列表加载失败'
  } finally {
    loaded.value = true
  }
}

async function refreshLocations(selectId?: number) {
  const rows = await api<LocationDTO[]>('/locations')
  locations.value = rows
  if (selectId != null) {
    setCurrentLocation(selectId)
  } else if (!rows.some((l) => l.id === currentLocationId.value)) {
    setCurrentLocation(rows[0]?.id ?? null)
  }
}

function setCurrentLocation(id: number | null) {
  currentLocationId.value = id
  if (id == null) localStorage.removeItem(STORAGE_KEY)
  else localStorage.setItem(STORAGE_KEY, String(id))
}

export function useLocation() {
  return {
    locations,
    currentLocationId,
    currentLocation,
    loaded,
    initError,
    init,
    refreshLocations,
    setCurrentLocation,
  }
}
