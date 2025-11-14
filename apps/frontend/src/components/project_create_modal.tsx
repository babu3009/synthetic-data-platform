import React, { useState, useEffect } from 'react'
import { Modal, Button, Form, Alert } from 'react-bootstrap'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createProject, checkProjectNameExists } from '../services/projects'
import { useToasts } from '../hooks/use_toasts'

interface ProjectCreateModalProps {
  show: boolean
  onClose: () => void
}

const ProjectCreateModal: React.FC<ProjectCreateModalProps> = ({ show, onClose }) => {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState('')
  const [webhookUrl, setWebhookUrl] = useState('')
  const [ttlDays, setTtlDays] = useState('')
  const [nameExists, setNameExists] = useState(false)
  const [checkingName, setCheckingName] = useState(false)
  const { push } = useToasts()
  const qc = useQueryClient()

  const mut = useMutation({
    mutationFn: () => createProject({ 
      name: name.trim(), 
      description: description.trim() || undefined,
      tags: tags.trim() ? tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      webhook_run_status_url: webhookUrl.trim() || undefined,
      artifact_ttl_days: ttlDays ? parseInt(ttlDays) : undefined
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects.all'] })
      push('success', 'Project created successfully')
      handleClose()
    },
    onError: (err: Error) => {
      push('error', err.message || 'Failed to create project')
    },
  })

  // Debounced name validation
  useEffect(() => {
    if (!name.trim()) {
      setNameExists(false)
      return
    }

    setCheckingName(true)
    const timer = setTimeout(async () => {
      const exists = await checkProjectNameExists(name.trim())
      setNameExists(exists)
      setCheckingName(false)
    }, 500)

    return () => clearTimeout(timer)
  }, [name])

  const handleClose = () => {
    setName('')
    setDescription('')
    setTags('')
    setWebhookUrl('')
    setTtlDays('')
    setNameExists(false)
    setCheckingName(false)
    onClose()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (nameExists || !name.trim()) return
    mut.mutate()
  }

  return (
    <Modal show={show} onHide={handleClose} centered>
      <Modal.Header closeButton>
        <Modal.Title>Create New Project</Modal.Title>
      </Modal.Header>
      <Form onSubmit={handleSubmit}>
        <Modal.Body>
          <Form.Group className="mb-3">
            <Form.Label>Project Name *</Form.Label>
            <Form.Control
              type="text"
              placeholder="Enter project name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoFocus
              isInvalid={nameExists}
              isValid={name.trim().length > 0 && !nameExists && !checkingName}
            />
            {checkingName && (
              <Form.Text className="text-muted">Checking availability...</Form.Text>
            )}
            {nameExists && (
              <Form.Control.Feedback type="invalid">
                A project with this name already exists
              </Form.Control.Feedback>
            )}
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Description (optional)</Form.Label>
            <Form.Control
              as="textarea"
              rows={3}
              placeholder="Enter project description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={1000}
            />
            <Form.Text className="text-muted">
              {description.length}/1000 characters
            </Form.Text>
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Tags (optional)</Form.Label>
            <Form.Control
              type="text"
              placeholder="tag1, tag2, tag3"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
            />
            <Form.Text className="text-muted">
              Comma-separated tags for organization
            </Form.Text>
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Run Status Webhook URL (optional)</Form.Label>
            <Form.Control
              type="url"
              placeholder="https://example.com/webhook"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
            <Form.Text className="text-muted">
              Receives job status POST callbacks
            </Form.Text>
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Artifact TTL Days (optional)</Form.Label>
            <Form.Control
              type="number"
              placeholder="30"
              min="0"
              value={ttlDays}
              onChange={(e) => setTtlDays(e.target.value)}
            />
            <Form.Text className="text-muted">
              Number of days to retain generated artifacts (files)
            </Form.Text>
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleClose} disabled={mut.isPending}>
            Cancel
          </Button>
          <Button 
            variant="primary" 
            type="submit" 
            disabled={mut.isPending || nameExists || !name.trim() || checkingName}
          >
            {mut.isPending ? 'Creating...' : 'Create Project'}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}

export default ProjectCreateModal
