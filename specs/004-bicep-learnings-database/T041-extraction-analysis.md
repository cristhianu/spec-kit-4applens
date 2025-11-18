# T041: Validation Rules Extraction Analysis

**Date**: 2025-11-01  
**Task**: Extract existing validation rules from speckit.validate.prompt.md  
**Status**: Analysis Complete

---

## Extraction Criteria

Per FR-004, extract rules with:
- **Normative keywords**: MUST, SHOULD, AVOID, ALWAYS, NEVER
- **Architectural patterns/anti-patterns**: Security patterns, network configurations, compliance requirements

---

## Rules Found in speckit.validate.prompt.md

### Security Section (Line 568-573)

| Line | Rule | Category | Already in DB? | Action |
|------|------|----------|----------------|--------|
| 568 | Secrets never logged in plain text - All secure values go through Key Vault | Security | ✅ Covered by Key Vault learning | Skip |
| 569 | Managed Identity preferred - Avoid storing credentials | Security | ✅ Already exists (line 7) | Skip |
| 570 | RBAC over access policies - Use role-based access control | Security | ❌ **NOT in database** | **Extract** |
| 571 | Audit trails enabled - Key Vault operations are logged | Operations | ❌ Partial (diagnostic settings) | **Extract** |
| 572 | Test environments isolated - No production resource access | Operations | N/A (operational) | Skip |
| 573 | Cleanup enabled by default - Minimizes security surface area | Operations | N/A (validation-specific) | Skip |

### Error Handling Section (Lines 237-461)

| Section | Rule | Category | Already in DB? | Action |
|---------|------|----------|----------------|--------|
| 242-251 | Missing required properties in Bicep templates (capture) | Configuration | ✅ Generic pattern exists | Skip |
| 244 | Invalid property values (capture) | Configuration | ✅ Generic pattern exists | Skip |
| 247 | Missing firewall rules (capture) | Networking | ❌ Specific pattern missing | **Extract** |
| 248 | Network security misconfigurations (capture) | Networking | ⚠️ Generic, needs specific | **Extract** |
| 249 | Storage/database connection string errors (capture) | Security | ✅ Covered by Managed Identity | Skip |
| 430 | Add required properties to Bicep template | Configuration | ✅ Generic pattern exists | Skip |
| 434 | Add firewall rule to allow Azure services | Networking | ❌ **NOT specific enough** | **Extract** |
| 440 | Grant required RBAC permissions or configure Managed Identity | Security | ⚠️ Split into 2 patterns | **Extract** |

### Best Practices Section (Line 555-567)

| Line | Rule | Category | Already in DB? | Action |
|------|------|----------|----------------|--------|
| 555 | Run validation in test environments only | Operations | N/A (operational) | Skip |
| 556 | Review validation summary | Operations | N/A (validation-specific) | Skip |
| 559 | Validate before production deployment | Operations | N/A (operational) | Skip |
| 561 | Use OpenAPI/Swagger for comprehensive testing | Configuration | N/A (testing-specific) | Skip |

---

## Rules to Extract (Summary)

### 1. RBAC Over Access Policies (Security - HIGH PRIORITY)
**Context**: Azure Key Vault  
**Issue**: Access policies used instead of RBAC  
**Solution**: Use Azure RBAC (enableRbacAuthorization: true) for Key Vault access control instead of access policies  
**Justification**: Aligns with SFI best practices, centralized IAM management

### 2. Audit Trails for Key Vault (Operations/Compliance - MEDIUM PRIORITY)
**Context**: Azure Key Vault  
**Issue**: Key Vault operations not audited  
**Solution**: Configure diagnostic settings for Key Vault with Log Analytics workspace to capture audit logs  
**Justification**: Compliance requirement, security monitoring

### 3. Firewall Rules for Azure Services (Networking - HIGH PRIORITY)
**Context**: Azure SQL Database, Storage Accounts  
**Issue**: Resources not accessible from Azure services  
**Solution**: Add firewall rule to allow Azure service IPs (startIpAddress: 0.0.0.0, endIpAddress: 0.0.0.0) or preferably use VNet integration  
**Justification**: Common deployment issue, but conflicts with SFI (prefer VNet integration)

### 4. RBAC Permissions for Managed Identity (Security - HIGH PRIORITY)
**Context**: Managed Identity authentication  
**Issue**: Managed Identity configured but lacks required permissions  
**Solution**: Grant appropriate Azure RBAC roles (e.g., Key Vault Secrets User, Storage Blob Data Contributor) to Managed Identity principal  
**Justification**: Common configuration issue after enabling Managed Identity

### 5. Network Security Group Configuration (Networking - MEDIUM PRIORITY)
**Context**: Subnets without NSG  
**Issue**: Subnet deployed without Network Security Group attached  
**Solution**: Create NSG with required rules and attach to subnet via networkSecurityGroup property  
**Justification**: Security baseline, traffic filtering

---

## Deduplication Analysis

### Existing Database Entries (26 total)

**Security (4 entries)**:
- Line 3: Storage public access → **SIMILAR** to rule #1 RBAC (different resource)
- Line 4: Key Vault public access → **DIFFERENT** from rule #1 (access method vs network)
- Line 5: SQL TLS version → **UNRELATED**
- Line 7: Managed Identity → **RELATED** to rule #4 (auth method, but rule #4 is about permissions)

**Networking (4 entries)**:
- Line 13: Front Door avoidance → **UNRELATED**
- Line 14: NSP vs Private Endpoints → **UNRELATED**
- Line 15: VNet Integration → **RELATED** to rule #3 (VNet is preferred over firewall)
- Line 16: Private DNS Zones → **UNRELATED**

**Compliance (1 entry)**:
- Line 11: Diagnostic settings → **SIMILAR** to rule #2 (audit trails are diagnostic settings)

### Deduplication Decisions

| Rule | Similar to Existing? | Decision |
|------|---------------------|----------|
| #1 RBAC over access policies | Partial (Managed Identity line 7) | **ADD** (different aspect - access control vs auth) |
| #2 Audit trails (Key Vault) | Yes (Diagnostic settings line 11) | **MERGE** - Update existing entry to be more specific |
| #3 Firewall rules | No exact match | **ADD with caveat** - Note VNet integration preferred (aligns with line 15) |
| #4 RBAC permissions for MI | Related to line 7 | **ADD** (different aspect - permissions vs configuration) |
| #5 NSG configuration | Partial (VNet line 15) | **ADD** (complementary - NSG is additional security layer) |

---

## Final Extraction List (New Entries)

### Entry 1: RBAC for Key Vault Access Control
```
[2025-11-01T00:00:00Z] Security Azure Key Vault → Access policies used instead of RBAC → Set enableRbacAuthorization: true in Key Vault properties for centralized IAM management
```

### Entry 2: Firewall Rules for Azure Services (with VNet caveat)
```
[2025-11-01T00:00:00Z] Networking Azure SQL Database → Service not accessible from Azure services → Add VNet integration with service endpoints OR firewall rule (startIpAddress: 0.0.0.0, endIpAddress: 0.0.0.0) if VNet not available
```

### Entry 3: RBAC Permissions for Managed Identity
```
[2025-11-01T00:00:00Z] Security Managed Identity → Configured but lacks required permissions → Grant Azure RBAC roles (e.g., Key Vault Secrets User, Storage Blob Data Contributor) to Managed Identity principal
```

### Entry 4: Network Security Group for Subnets
```
[2025-11-01T00:00:00Z] Networking Subnet Configuration → Deployed without Network Security Group → Create NSG resource and attach via subnet's networkSecurityGroup property for traffic filtering
```

### Entry 5: Key Vault Audit Logging (Update Existing)
**Existing entry** (line 11):
```
[2025-11-01T00:00:00Z] Compliance All Resources → Missing diagnostic settings → Configure diagnosticSettings with Log Analytics workspace for audit compliance
```

**Updated entry** (more specific for Key Vault):
```
[2025-11-01T00:00:00Z] Compliance Azure Key Vault → Key Vault operations not audited → Configure diagnosticSettings with Log Analytics workspace and enable AuditEvent logs for compliance
```

---

## Extraction Summary

- **Total rules analyzed**: 14 rules from speckit.validate.prompt.md
- **Rules to extract**: 4 new entries + 1 update
- **Rules to skip**: 9 (duplicates, operational guidance, or too generic)
- **Deduplication checks**: 5 similarity comparisons with existing 26 entries
- **Final database size**: 30 entries (26 existing + 4 new)

---

## Next Steps (T042)

1. Add 4 new entries to `.specify/learnings/bicep-learnings.md`:
   - Entry 1: RBAC for Key Vault (Security section)
   - Entry 2: Firewall rules (Networking section)
   - Entry 3: RBAC permissions for MI (Security section)
   - Entry 4: NSG for subnets (Networking section)

2. Update 1 existing entry:
   - Line 11: Make Key Vault audit logging more specific

3. Update total count: 26 → 30 entries

4. Proceed to T043: Update speckit.validate prompt to load learnings database

---

*Analysis complete. Ready for implementation.*
