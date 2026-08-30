CREATE TABLE `applications` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`opportunity_id` integer,
	`company` text NOT NULL,
	`title` text NOT NULL,
	`status` text DEFAULT 'saved' NOT NULL,
	`applied_at` integer,
	`next_action` text,
	`next_action_at` integer,
	`notes` text,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL,
	FOREIGN KEY (`opportunity_id`) REFERENCES `opportunities`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `opportunities` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`external_id` text NOT NULL,
	`company` text NOT NULL,
	`title` text NOT NULL,
	`location` text NOT NULL,
	`season` text NOT NULL,
	`role_family` text NOT NULL,
	`description` text,
	`source_url` text NOT NULL,
	`keywords` text DEFAULT '[]' NOT NULL,
	`first_seen_at` integer NOT NULL,
	`last_seen_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `opportunities_external_id_unique` ON `opportunities` (`external_id`);--> statement-breakpoint
CREATE TABLE `preferences` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`retention_days` integer DEFAULT 365 NOT NULL,
	`refresh_minutes` integer DEFAULT 30 NOT NULL,
	`alerts_enabled` integer DEFAULT true NOT NULL
);
