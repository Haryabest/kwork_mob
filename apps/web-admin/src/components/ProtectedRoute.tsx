import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { canAccess, defaultRouteFor } from '../auth/roles';

export default function ProtectedRoute() {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!canAccess(user.role, location.pathname)) {
    return <Navigate to={defaultRouteFor(user.role)} replace />;
  }

  return <Outlet />;
}
