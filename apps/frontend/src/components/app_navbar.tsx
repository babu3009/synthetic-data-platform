import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Navbar as BsNavbar, Nav, Container } from 'react-bootstrap'
import { useAuth } from '../state/use_auth'
import ProjectSelectorModal from './project_selector'

function AppNavbar() {
  const location = useLocation()
  // Derive a current projectId from URL if present so links can be project-scoped
  const projectMatch = location.pathname.match(/\/projects\/([^/]+)/)
  const projectId = projectMatch ? projectMatch[1] : undefined
  const llmSettingsHref = projectId ? `/projects/${projectId}/llm-settings` : '/projects/placeholder/llm-settings'
  const wizardHref = projectId ? `/projects/${projectId}/wizard` : '/wizard'
  const llmProvidersHref = projectId ? `/admin/${projectId}/llm-providers` : '/admin/llm-providers'
  const [showPicker, setShowPicker] = React.useState(false)
  const [pendingAction, setPendingAction] = React.useState<'settings' | 'providers' | 'wizard' | null>(null)
  const navigate = useNavigate()

  function handleNavigate(target: 'settings' | 'providers' | 'wizard') {
    if (projectId) {
      if (target === 'settings') navigate(llmSettingsHref)
      else if (target === 'providers') navigate(llmProvidersHref)
      else navigate(wizardHref)
    } else {
      setPendingAction(target)
      setShowPicker(true)
    }
  }
  const { token, logout, role } = useAuth()
  return (
    <BsNavbar bg="dark" variant="dark" expand="lg" sticky="top">
      <Container>
        <BsNavbar.Brand as={Link} to="/">
          <strong>Synthetic Data Platform</strong>
        </BsNavbar.Brand>
        <BsNavbar.Toggle aria-controls="basic-navbar-nav" />
        <BsNavbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link as={Link} to="/" active={location.pathname === '/'}>Home</Nav.Link>
            <Nav.Link as={Link} to="/projects" active={location.pathname === '/projects'}>Projects</Nav.Link>
            <Nav.Link
              as={Link}
              to={wizardHref}
              onClick={(e) => { if (!projectId) { e.preventDefault(); handleNavigate('wizard') } }}
              active={/\/wizard$/.test(location.pathname)}
              aria-label="Data Wizard"
            >
              Data Wizard
            </Nav.Link>
            <Nav.Link as={Link} to="/datasets" active={location.pathname === '/datasets'}>Datasets</Nav.Link>
            <Nav.Link as={Link} to="/analytics" active={location.pathname === '/analytics'}>Analytics</Nav.Link>
            <Nav.Link
              as={Link}
              to={llmSettingsHref}
              onClick={(e) => { if (!projectId) { e.preventDefault(); handleNavigate('settings') } }}
              active={/llm-settings$/.test(location.pathname)}
              aria-label="LLM Settings"
            >
              LLM Settings
            </Nav.Link>
            {role === 'OWNER' && (
              <Nav.Link
                as={Link}
                to={llmProvidersHref}
                onClick={(e) => { if (!projectId) { e.preventDefault(); handleNavigate('providers') } }}
                active={/llm-providers$/.test(location.pathname)}
                aria-label="LLM Providers Admin"
              >
                LLM Providers
              </Nav.Link>
            )}
            {role === 'OWNER' && (
              <Nav.Link
                as={Link}
                to="/admin/users"
                active={/\/admin\/users$/.test(location.pathname)}
                aria-label="Admin User Approval"
              >
                Admin Users
              </Nav.Link>
            )}
              <Nav.Link
                as={Link}
                to="/flat/preview"
                active={/\/flat\/preview$/.test(location.pathname)}
                aria-label="Flat Preview"
              >
                Flat Preview
              </Nav.Link>
          </Nav>
          <Nav>
            {token ? (
              <>
                <Nav.Link as={Link} to="/profile" active={location.pathname === '/profile'}>Profile</Nav.Link>
                <Nav.Link onClick={logout} aria-label="Logout">Logout</Nav.Link>
              </>
            ) : (
              <Nav.Link as={Link} to="/login" active={location.pathname === '/login'}>Login</Nav.Link>
            )}
          </Nav>
        </BsNavbar.Collapse>
      </Container>
      <ProjectSelectorModal
        show={showPicker}
        onClose={() => setShowPicker(false)}
        onSelect={(pid) => {
          setShowPicker(false)
          if (pendingAction === 'settings') navigate(`/projects/${pid}/llm-settings`)
          else if (pendingAction === 'providers') navigate(`/admin/${pid}/llm-providers`)
          else navigate(`/projects/${pid}/wizard`)
          setPendingAction(null)
        }}
      />
    </BsNavbar>
  )
}

export default AppNavbar
export { AppNavbar }
