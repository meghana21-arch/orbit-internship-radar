import { integer, sqliteTable, text } from 'drizzle-orm/sqlite-core';

export const opportunities = sqliteTable('opportunities', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  externalId: text('external_id').notNull().unique(),
  company: text('company').notNull(),
  title: text('title').notNull(),
  location: text('location').notNull(),
  season: text('season').notNull(),
  roleFamily: text('role_family').notNull(),
  description: text('description'),
  sourceUrl: text('source_url').notNull(),
  keywords: text('keywords').notNull().default('[]'),
  firstSeenAt: integer('first_seen_at', { mode: 'timestamp' }).notNull(),
  lastSeenAt: integer('last_seen_at', { mode: 'timestamp' }).notNull(),
});

export const applications = sqliteTable('applications', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  opportunityId: integer('opportunity_id').references(() => opportunities.id),
  company: text('company').notNull(),
  title: text('title').notNull(),
  status: text('status').notNull().default('saved'),
  appliedAt: integer('applied_at', { mode: 'timestamp' }),
  nextAction: text('next_action'),
  nextActionAt: integer('next_action_at', { mode: 'timestamp' }),
  notes: text('notes'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

export const preferences = sqliteTable('preferences', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  retentionDays: integer('retention_days').notNull().default(365),
  refreshMinutes: integer('refresh_minutes').notNull().default(30),
  alertsEnabled: integer('alerts_enabled', { mode: 'boolean' }).notNull().default(true),
});
