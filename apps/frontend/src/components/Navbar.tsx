import { Navbar as BsNavbar, Nav, Container } from 'react-bootstrap'
import { Link, useLocation } from 'react-router-dom'

function Navbar() {
  const location = useLocation()

  return (
    <BsNavbar bg="dark" variant="dark" expand="lg" sticky="top">
      <Container>
        <BsNavbar.Brand as={Link} to="/">
          <strong>Synthetic Data Platform</strong>
        </BsNavbar.Brand>
        
        <BsNavbar.Toggle aria-controls="basic-navbar-nav" />
        
        <BsNavbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link 
              as={Link} 
              to="/" 
              active={location.pathname === '/'}
            >
              Home
            </Nav.Link>
            <Nav.Link 
              as={Link} 
              to="/wizard" 
              active={location.pathname === '/wizard'}
            >
              Data Wizard
            </Nav.Link>
            <Nav.Link 
              as={Link} 
              to="/datasets" 
              active={location.pathname === '/datasets'}
            >
              Datasets
            </Nav.Link>
            <Nav.Link 
              as={Link} 
              to="/analytics" 
              active={location.pathname === '/analytics'}
            >
              Analytics
            </Nav.Link>
          </Nav>
          
          <Nav>
            <Nav.Link 
              as={Link} 
              to="/profile" 
              active={location.pathname === '/profile'}
            >
              Profile
            </Nav.Link>
          </Nav>
        </BsNavbar.Collapse>
      </Container>
    </BsNavbar>
  )
}

export default Navbar