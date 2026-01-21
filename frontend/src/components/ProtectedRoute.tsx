/**
 * Protected route component that requires authentication.
 */

import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/useAuthStore'
import { useEffect } from 'react'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation()
  const { isAuthenticated, accessToken, fetchUser, user } = useAuthStore()

  useEffect(() => {
    // Fetch user data if authenticated but user not loaded
    if (isAuthenticated && accessToken && !user) {
      fetchUser()
    }
  }, [isAuthenticated, accessToken, user, fetchUser])

  if (!isAuthenticated || !accessToken) {
    // Redirect to login page, but save the attempted URL
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
