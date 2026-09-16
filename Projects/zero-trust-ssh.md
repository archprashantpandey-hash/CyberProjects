---

```markdown
# Zero-Trust Ephemeral SSH Gateway

## Status

Researching

## Category

Security

## One-Line Idea

A temporary SSH access system based on short-lived OpenSSH certificates.

---

## Problem

Permanent SSH keys can remain valid long after temporary access is required.

---

## Proposed Solution

Use a small certificate authority to issue short-lived SSH certificates.

For example, access could expire automatically after 15 minutes.

---

## Architecture

```text
User
 │
 ↓
Access Request
 │
 ↓
Certificate Authority
 │
 ↓
Short-Lived SSH Certificate
 │
 ↓
Target Server