/**
 * API service for communicating with the backend.
 */

import { useAuthStore } from '../stores/useAuthStore'

const BASE_URL = '/api/v1'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function getAuthHeaders(): HeadersInit {
  const accessToken = useAuthStore.getState().accessToken
  if (accessToken) {
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    }
  }
  return {
    'Content-Type': 'application/json',
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    // Try to refresh token
    const refreshed = await useAuthStore.getState().refreshAccessToken()
    if (!refreshed) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    throw new ApiError(401, 'Unauthorized - please log in again')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new ApiError(response.status, error.detail || response.statusText)
  }
  return response.json()
}

export const api = {
  async get<T = unknown>(path: string): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      headers: getAuthHeaders(),
    })
    return handleResponse<T>(response)
  },

  async post<T = unknown>(path: string, data?: unknown): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: data ? JSON.stringify(data) : undefined,
    })
    return handleResponse<T>(response)
  },

  async put<T = unknown>(path: string, data: unknown): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse<T>(response)
  },

  async delete(path: string): Promise<void> {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    })
    if (!response.ok) {
      if (response.status === 401) {
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return
      }
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new ApiError(response.status, error.detail || response.statusText)
    }
  },
}

export { ApiError }
