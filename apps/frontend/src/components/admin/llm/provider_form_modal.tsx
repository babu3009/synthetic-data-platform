import React from 'react'
import { Modal, Button, Form, Row, Col } from 'react-bootstrap'
import { useForm } from 'react-hook-form'
import { useCreateLlmProvider } from '../../../hooks/use_llm_admin'

interface Props {
  projectId: string
  show: boolean
  onHide: () => void
}

type FormValues = {
  kind: 'openai' | 'anthropic' | 'ollama' | 'lmstudio'
  name: string
  base_url: string
  is_enabled: boolean
}

const defaultBaseUrl: Record<FormValues['kind'], string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com/v1',
  ollama: 'http://localhost:11434',
  lmstudio: 'http://localhost:1234/v1',
}

export function ProviderFormModal({ projectId, show, onHide }: Props) {
  const { register, handleSubmit, watch, reset } = useForm<FormValues>({
    defaultValues: { kind: 'openai', name: 'openai', base_url: defaultBaseUrl.openai, is_enabled: true },
  })
  const kind = watch('kind')
  const createMut = useCreateLlmProvider(projectId)

  const onSubmit = (data: FormValues) => {
    createMut.mutate(data, {
      onSuccess: () => {
        reset()
        onHide()
      },
    })
  }

  React.useEffect(() => {
    // Auto-fill base_url when switching kind if user hasn't modified it
    reset({ kind, name: kind, base_url: defaultBaseUrl[kind], is_enabled: true })
  }, [kind, reset])

  return (
    <Modal show={show} onHide={onHide} backdrop="static" size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Add LLM Provider</Modal.Title>
      </Modal.Header>
      <Form onSubmit={handleSubmit(onSubmit)}>
        <Modal.Body>
          <Row className="mb-3">
            <Col md={4}>
              <Form.Group>
                <Form.Label>Kind</Form.Label>
                <Form.Select aria-label="Provider kind" {...register('kind')}>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="ollama">Ollama</option>
                  <option value="lmstudio">LM Studio</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group>
                <Form.Label>Name</Form.Label>
                <Form.Control {...register('name', { required: true })} />
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group>
                <Form.Label>Enabled</Form.Label>
                <Form.Check type="switch" {...register('is_enabled')} />
              </Form.Group>
            </Col>
          </Row>
          <Form.Group className="mb-3">
            <Form.Label>Base URL</Form.Label>
            <Form.Control {...register('base_url', { required: true })} />
          </Form.Group>
          {createMut.isError && (
            <div className="text-danger small">Error creating provider</div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onHide} disabled={createMut.isLoading}>Cancel</Button>
          <Button variant="primary" type="submit" disabled={createMut.isLoading}>Create</Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}
