import { z } from 'zod'

// Provider types
export const ProviderTypeEnum = z.enum([
  'faker',
  'pattern',
  'sequence',
  'categorical',
  'expression',
  'geo',
  'checksum-valid',
  'reference',
  'empirical',
])
export type ProviderType = z.infer<typeof ProviderTypeEnum>

// Distribution config
export const DistributionConfigSchema = z
  .record(z.number().min(0, 'probabilities must be >= 0'))
  .refine((obj: Record<string, number>) => Object.keys(obj).length > 0, {
    message: 'distribution must have at least one category',
  })
  .refine((obj: Record<string, number>) => {
    const sum = (Object.values(obj) as number[]).reduce((a, b) => a + b, 0)
    return sum > 0
  }, { message: 'distribution probabilities must sum to > 0' })
export type DistributionConfig = z.infer<typeof DistributionConfigSchema>

// Provider configs (typed union of common shapes)
export const FakerConfigSchema = z.object({ method: z.string(), args: z.array(z.unknown()).optional() })
export const PatternConfigSchema = z.object({ regex: z.string() })
export const SequenceConfigSchema = z.object({ start: z.number().optional(), step: z.number().optional(), pad: z.number().optional() })
export const CategoricalConfigSchema = z.object({ values: z.array(z.string()), probs: z.array(z.number()).optional() })
export const ExpressionConfigSchema = z.object({ expr: z.string() })
export const GeoConfigSchema = z.object({ country: z.string().optional(), format: z.enum(['latlong','point','polygon']).optional() })
export const ChecksumValidConfigSchema = z.object({ kind: z.enum(['luhn','iban','imei']).optional() })
export const ReferenceConfigSchema = z.object({ table: z.string(), column: z.string(), weighted: z.boolean().optional() })
export const EmpiricalConfigSchema = z.object({ histogram: DistributionConfigSchema })

export const ProviderConfigSchema = z.union([
  FakerConfigSchema,
  PatternConfigSchema,
  SequenceConfigSchema,
  CategoricalConfigSchema,
  ExpressionConfigSchema,
  GeoConfigSchema,
  ChecksumValidConfigSchema,
  ReferenceConfigSchema,
  EmpiricalConfigSchema,
  z.record(z.string(), z.unknown()), // fallback generic
])
export type ProviderConfig = z.infer<typeof ProviderConfigSchema>

// Column definition
export const ColumnDefSchema = z.object({
  name: z.string().min(1),
  dtype: z.string().min(1),
  nullable: z.boolean(),
  regex: z.string().optional(),
  distribution: z.string().optional(),
  pii: z.boolean().optional(),
  piiSubtype: z
    .enum(['email', 'phone', 'address', 'national_id', 'credit_card', 'dob', 'ip', 'device'])
    .optional(),
  provider: ProviderTypeEnum.optional(),
  providerConfig: ProviderConfigSchema.optional(),
})
export type ColumnDef = z.infer<typeof ColumnDefSchema>

// Row target policy
export const RowTargetSchema = z.union([
  z.object({ type: z.literal('absolute'), value: z.number().int().min(0) }),
  z.object({ type: z.literal('ratioTo'), table: z.string().min(1), ratio: z.number().positive() }),
])
export type RowTarget = z.infer<typeof RowTargetSchema>

// Table definition
export const TableDefSchema = z.object({
  name: z.string().min(1),
  columns: z.array(ColumnDefSchema).min(1),
  pk: z.array(z.string()).optional(),
  uniques: z.array(z.array(z.string()).min(1)).optional(),
  rowTarget: RowTargetSchema.optional(),
})
export type TableDef = z.infer<typeof TableDefSchema>

// Foreign key definition
export const FKDefSchema = z.object({
  name: z.string().optional(),
  sourceTable: z.string().min(1),
  sourceColumn: z.string().min(1),
  targetTable: z.string().min(1),
  targetColumn: z.string().min(1),
  onDelete: z.enum(['cascade', 'restrict', 'set_null', 'no_action']).optional(),
})
export type FKDef = z.infer<typeof FKDefSchema>

// Relationship (optional, mirrors FK with cardinality)
export const RelationshipSchema = z.object({
  id: z.string().min(1),
  sourceTable: z.string(),
  sourceColumn: z.string(),
  targetTable: z.string(),
  targetColumn: z.string(),
  cardinality: z.enum(['ONE_TO_ONE', 'ONE_TO_MANY', 'MANY_TO_MANY']),
})
export type Relationship = z.infer<typeof RelationshipSchema>

// Entity schema
export const EntitySchemaSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  description: z.string().optional(),
  version: z.number().optional(),
  tables: z.array(TableDefSchema).min(1),
  updatedAt: z.string().optional(),
  relationships: z.array(RelationshipSchema).optional(),
  layout: z
    .record(z.string(), z.object({ x: z.number(), y: z.number() }))
    .optional(),
  rulesConfig: z.string().optional(),
  rulesFormat: z.enum(['yaml', 'json']).optional(),
})
export type EntitySchema = z.infer<typeof EntitySchemaSchema>
export type EntitySchemaCreate = Omit<EntitySchema, 'id' | 'updatedAt'>
export type EntitySchemaUpdate = Partial<Omit<EntitySchema, 'id' | 'updatedAt'>>

// Rules definitions (align with services/validation)
export const ImplicationRuleSchema = z.object({
  type: z.literal('implication'),
  table: z.string(),
  when: z.string(),
  then: z.array(z.string()).min(1),
})
export const UniquenessRuleSchema = z.object({
  type: z.literal('uniqueness'),
  table: z.string(),
  columns: z.array(z.string()).min(1),
})
export const DistributionRuleSchema = z.object({
  type: z.literal('distribution'),
  table: z.string(),
  column: z.string(),
  probs: DistributionConfigSchema,
})
export const TemporalRuleSchema = z.object({
  type: z.literal('temporal'),
  table: z.string(),
  left: z.string(),
  op: z.enum(['<=', '<', '>=', '>', '==', '!=']),
  right: z.object({ column: z.string(), offset_days: z.number().int() }),
})

export const RuleSchema = z.union([
  ImplicationRuleSchema,
  UniquenessRuleSchema,
  DistributionRuleSchema,
  TemporalRuleSchema,
])
export type Rule = z.infer<typeof RuleSchema>
export const RulesDefSchema = z.array(RuleSchema)
export type RulesDef = z.infer<typeof RulesDefSchema>
