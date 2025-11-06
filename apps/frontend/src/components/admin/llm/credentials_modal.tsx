import React from 'react'
import { Modal, Button, Form, Row, Col, Spinner } from 'react-bootstrap'
import { useForm } from 'react-hook-form'
import { useUpsertLlmCredentials } from '../../../hooks/use_llm_admin'

interface Props {
  projectId: string
  providerId: string
  show: boolean
  onHide: () => void
  masked?: { api_key?: string; org_id?: string }
}

type FormValues = {
  api_key: string
  org_id: string
  extraJson: string
}

export function CredentialsModal({ projectId, providerId, show, onHide, masked }: Props) {
  const { register, handleSubmit, reset } = useForm<FormValues>({
    defaultValues: { api_key: '', org_id: '', extraJson: '{}' },
  })
  const mut = useUpsertLlmCredentials(projectId, providerId)

  const onSubmit = (data: FormValues) => {
    let extra: Record<string, unknown> = {}
    try {
      extra = JSON.parse(data.extraJson || '{}')
    } catch (_) {
      // ignore parse error; send empty
    }
    mut.mutate(
      { api_key: data.api_key || null, org_id: data.org_id || null, extra },
      {
        onSuccess: () => {
          reset({ api_key: '', org_id: '', extraJson: '{}' })
          onHide()
        },
      }
    )
  }

  return (
    <Modal show={show} onHide={onHide} backdrop="static" size="lg">
      <Modal.Header closeButton>
        <Modal.Title>Manage Credentials</Modal.Title>
      </Modal.Header>
      <Form onSubmit={handleSubmit(onSubmit)}>
        <Modal.Body>
          <Row className="mb-3">
            <Col md={6}>
              <Form.Group>
                <Form.Label>API Key</Form.Label>
                <Form.Control type="password" placeholder={masked?.api_key ? '••••••••' : 'sk-...'} {...register('api_key')} />
              </Form.Group>
            </Col>
            <Col md={6}>
              <Form.Group>
                <Form.Label>Org ID</Form.Label>
                <Form.Control placeholder={masked?.org_id ? '••••••••' : ''} {...register('org_id')} />
              </Form.Group>
            </Col>
          </Row>
          <Form.Group className="mb-3">
            <Form.Label>Extra (JSON)</Form.Label>
            <Form.Control as="textarea" rows={4} {...register('extraJson')} />
          </Form.Group>
          {mut.isError && (
            <div className="text-danger small">Error saving credentials</div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={onHide} disabled={mut.isLoading}>Cancel</Button>
          <Button variant="primary" type="submit" disabled={mut.isLoading}>
            {mut.isLoading ? <Spinner size="sm" /> : 'Save'}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  )
}
