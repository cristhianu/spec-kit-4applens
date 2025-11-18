#!/usr/bin/env python3
"""
Bicep Architecture Validation Script

Validates generated Bicep templates for Secure Future Initiative (SFI) compliance.
Checks for architectural patterns documented in the learnings database.

Exit Codes:
    0 - All checks passed (SFI compliant)
    1 - Validation violations found
    2 - Script error (invalid arguments, file not found, etc.)

Usage:
    python scripts/bicep_validate_architecture.py <bicep-file> [options]
    
Options:
    --allow-front-door      Allow Azure Front Door resources (skip Front Door check)
    --verbose               Show detailed validation output
    --json                  Output results in JSON format
    
Examples:
    # Validate a Bicep template
    python scripts/bicep_validate_architecture.py main.bicep
    
    # Allow Front Door for CDN scenario
    python scripts/bicep_validate_architecture.py main.bicep --allow-front-door
    
    # CI/CD integration
    python scripts/bicep_validate_architecture.py main.bicep || exit 1
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Tuple, Optional


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    passed: bool
    message: str
    severity: str = "error"  # error, warning, info
    line_number: Optional[int] = None
    resource_name: Optional[str] = None


class BicepValidator:
    """Validates Bicep templates for SFI compliance."""
    
    # Azure resource type patterns
    FRONT_DOOR_TYPES = [
        r"Microsoft\.Cdn/profiles",
        r"Microsoft\.Network/frontDoors",
    ]
    
    NSP_TYPES = [
        r"Microsoft\.Network/networkSecurityPerimeters",
    ]
    
    PRIVATE_ENDPOINT_TYPE = r"Microsoft\.Network/privateEndpoints"
    
    DATA_SERVICE_TYPES = [
        r"Microsoft\.Storage/storageAccounts",
        r"Microsoft\.Sql/servers",
        r"Microsoft\.KeyVault/vaults",
        r"Microsoft\.DocumentDB/databaseAccounts",  # Cosmos DB
        r"Microsoft\.DBforMySQL/servers",
        r"Microsoft\.DBforPostgreSQL/servers",
        r"Microsoft\.Cache/redis",  # Azure Redis Cache
    ]
    
    def __init__(self, bicep_file: Path, allow_front_door: bool = False, verbose: bool = False):
        """
        Initialize validator.
        
        Args:
            bicep_file: Path to Bicep template file
            allow_front_door: Whether to allow Front Door resources
            verbose: Whether to show detailed output
        """
        self.bicep_file = bicep_file
        self.allow_front_door = allow_front_door
        self.verbose = verbose
        self.results: List[ValidationResult] = []
        
        if not bicep_file.exists():
            raise FileNotFoundError(f"Bicep file not found: {bicep_file}")
        
        self.content = bicep_file.read_text(encoding='utf-8')
        self.lines = self.content.split('\n')
    
    def validate(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all checks passed, False otherwise
        """
        self.results = []
        
        # Run all checks
        self.check_no_front_door()
        self.check_no_network_security_perimeter()
        self.check_private_endpoints_recommended()
        self.check_public_network_access_disabled()
        self.check_vnet_integration()
        self.check_managed_identity()
        self.check_tls_version()
        self.check_https_only()
        
        # Return overall result
        return all(r.passed for r in self.results if r.severity == "error")
    
    def check_no_front_door(self) -> None:
        """Check that Azure Front Door is not used unless explicitly allowed."""
        if self.allow_front_door:
            self.results.append(ValidationResult(
                check_name="No Front Door",
                passed=True,
                message="Front Door check skipped (--allow-front-door flag set)",
                severity="info"
            ))
            return
        
        violations = []
        for line_num, line in enumerate(self.lines, start=1):
            for pattern in self.FRONT_DOOR_TYPES:
                if re.search(pattern, line, re.IGNORECASE):
                    # Extract resource name if possible
                    resource_match = re.search(r"resource\s+(\w+)", line)
                    resource_name = resource_match.group(1) if resource_match else "unknown"
                    violations.append((line_num, resource_name, pattern))
        
        if violations:
            messages = [f"Line {ln}: {rn} ({pat})" for ln, rn, pat in violations]
            self.results.append(ValidationResult(
                check_name="No Front Door",
                passed=False,
                message=f"Azure Front Door detected (use --allow-front-door if intentional): {'; '.join(messages)}",
                severity="error",
                line_number=violations[0][0],
                resource_name=violations[0][1]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="No Front Door",
                passed=True,
                message="No Azure Front Door resources found ✓",
                severity="info"
            ))
    
    def check_no_network_security_perimeter(self) -> None:
        """Check that Network Security Perimeter is not used (prefer Private Endpoints)."""
        violations = []
        for line_num, line in enumerate(self.lines, start=1):
            for pattern in self.NSP_TYPES:
                if re.search(pattern, line, re.IGNORECASE):
                    resource_match = re.search(r"resource\s+(\w+)", line)
                    resource_name = resource_match.group(1) if resource_match else "unknown"
                    violations.append((line_num, resource_name))
        
        if violations:
            messages = [f"Line {ln}: {rn}" for ln, rn in violations]
            self.results.append(ValidationResult(
                check_name="No Network Security Perimeter",
                passed=False,
                message=f"Network Security Perimeter detected (use Private Endpoints instead): {'; '.join(messages)}",
                severity="error",
                line_number=violations[0][0],
                resource_name=violations[0][1]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="No Network Security Perimeter",
                passed=True,
                message="No Network Security Perimeter resources found ✓",
                severity="info"
            ))
    
    def check_private_endpoints_recommended(self) -> None:
        """Check that Private Endpoints are used for data services."""
        has_data_services = any(
            re.search(pattern, self.content, re.IGNORECASE)
            for pattern in self.DATA_SERVICE_TYPES
        )
        
        has_private_endpoints = bool(re.search(
            self.PRIVATE_ENDPOINT_TYPE, self.content, re.IGNORECASE
        ))
        
        if has_data_services and not has_private_endpoints:
            self.results.append(ValidationResult(
                check_name="Private Endpoints Recommended",
                passed=False,
                message="Data services detected without Private Endpoints (SFI requires Private Endpoints)",
                severity="warning"
            ))
        elif has_private_endpoints:
            self.results.append(ValidationResult(
                check_name="Private Endpoints Recommended",
                passed=True,
                message="Private Endpoints configured ✓",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Private Endpoints Recommended",
                passed=True,
                message="No data services requiring Private Endpoints",
                severity="info"
            ))
    
    def check_public_network_access_disabled(self) -> None:
        """Check that publicNetworkAccess is disabled for data services."""
        violations = []
        
        # Find all data service resources
        for line_num, line in enumerate(self.lines, start=1):
            for pattern in self.DATA_SERVICE_TYPES:
                if re.search(pattern, line, re.IGNORECASE):
                    # Found a data service, check for publicNetworkAccess in following lines
                    resource_match = re.search(r"resource\s+(\w+)", line)
                    resource_name = resource_match.group(1) if resource_match else "unknown"
                    
                    # Look ahead for properties section (next 50 lines)
                    found_disabled = False
                    for offset in range(1, min(50, len(self.lines) - line_num + 1)):
                        check_line = self.lines[line_num - 1 + offset]
                        
                        # Check if publicNetworkAccess is set
                        if re.search(r"publicNetworkAccess\s*:\s*['\"]?Disabled['\"]?", check_line, re.IGNORECASE):
                            found_disabled = True
                            break
                        elif re.search(r"publicNetworkAccess\s*:\s*['\"]?Enabled['\"]?", check_line, re.IGNORECASE):
                            violations.append((line_num, resource_name, "Enabled"))
                            break
                    
                    # If no publicNetworkAccess found, it's a warning (defaults vary)
                    if not found_disabled and not any(v[1] == resource_name for v in violations):
                        violations.append((line_num, resource_name, "Not Set"))
        
        if violations:
            messages = [f"Line {ln}: {rn} ({status})" for ln, rn, status in violations]
            severity = "error" if any(v[2] == "Enabled" for v in violations) else "warning"
            self.results.append(ValidationResult(
                check_name="Public Network Access Disabled",
                passed=False,
                message=f"Data services should have publicNetworkAccess: 'Disabled': {'; '.join(messages)}",
                severity=severity,
                line_number=violations[0][0],
                resource_name=violations[0][1]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Public Network Access Disabled",
                passed=True,
                message="All data services have publicNetworkAccess disabled ✓",
                severity="info"
            ))
    
    def check_vnet_integration(self) -> None:
        """Check that VNet integration is configured for compute services."""
        has_compute = bool(re.search(
            r"Microsoft\.(Web|ContainerApp|Compute)/",
            self.content,
            re.IGNORECASE
        ))
        
        has_vnet = bool(re.search(
            r"Microsoft\.Network/virtualNetworks",
            self.content,
            re.IGNORECASE
        ))
        
        has_vnet_config = bool(re.search(
            r"(virtualNetworkSubnetId|vnetConfiguration|vnetRouteAllEnabled)",
            self.content,
            re.IGNORECASE
        ))
        
        if has_compute and not (has_vnet and has_vnet_config):
            self.results.append(ValidationResult(
                check_name="VNet Integration",
                passed=False,
                message="Compute services detected without VNet integration (SFI requires network isolation)",
                severity="warning"
            ))
        elif has_vnet and has_vnet_config:
            self.results.append(ValidationResult(
                check_name="VNet Integration",
                passed=True,
                message="VNet integration configured ✓",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="VNet Integration",
                passed=True,
                message="No compute services requiring VNet integration",
                severity="info"
            ))
    
    def check_managed_identity(self) -> None:
        """Check that Managed Identity is used for authentication."""
        has_compute = bool(re.search(
            r"Microsoft\.(Web|ContainerApp|Compute|Logic|DataFactory)/",
            self.content,
            re.IGNORECASE
        ))
        
        has_managed_identity = bool(re.search(
            r"identity\s*:\s*\{\s*type\s*:\s*['\"]?(SystemAssigned|UserAssigned)",
            self.content,
            re.IGNORECASE
        ))
        
        if has_compute and not has_managed_identity:
            self.results.append(ValidationResult(
                check_name="Managed Identity",
                passed=False,
                message="Compute services should use Managed Identity for authentication",
                severity="warning"
            ))
        elif has_managed_identity:
            self.results.append(ValidationResult(
                check_name="Managed Identity",
                passed=True,
                message="Managed Identity configured ✓",
                severity="info"
            ))
        else:
            self.results.append(ValidationResult(
                check_name="Managed Identity",
                passed=True,
                message="No services requiring Managed Identity",
                severity="info"
            ))
    
    def check_tls_version(self) -> None:
        """Check that TLS 1.2 or higher is enforced."""
        violations = []
        
        # Check for TLS version settings
        tls_patterns = [
            (r"minimumTlsVersion\s*:\s*['\"]?TLS1_0['\"]?", "TLS1_0"),
            (r"minimumTlsVersion\s*:\s*['\"]?TLS1_1['\"]?", "TLS1_1"),
            (r"minimalTlsVersion\s*:\s*['\"]?1\.0['\"]?", "1.0"),
            (r"minimalTlsVersion\s*:\s*['\"]?1\.1['\"]?", "1.1"),
            (r"minTlsVersion\s*:\s*['\"]?1\.0['\"]?", "1.0"),
            (r"minTlsVersion\s*:\s*['\"]?1\.1['\"]?", "1.1"),
        ]
        
        for line_num, line in enumerate(self.lines, start=1):
            for pattern, version in tls_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append((line_num, version))
        
        if violations:
            messages = [f"Line {ln}: {ver}" for ln, ver in violations]
            self.results.append(ValidationResult(
                check_name="TLS Version",
                passed=False,
                message=f"TLS version should be 1.2 or higher: {'; '.join(messages)}",
                severity="error",
                line_number=violations[0][0]
            ))
        else:
            # Check if TLS is configured at all
            has_tls_config = bool(re.search(
                r"(minimumTlsVersion|minimalTlsVersion|minTlsVersion)",
                self.content,
                re.IGNORECASE
            ))
            
            if has_tls_config:
                self.results.append(ValidationResult(
                    check_name="TLS Version",
                    passed=True,
                    message="TLS 1.2+ enforced ✓",
                    severity="info"
                ))
            else:
                self.results.append(ValidationResult(
                    check_name="TLS Version",
                    passed=True,
                    message="No TLS version configuration found (using defaults)",
                    severity="info"
                ))
    
    def check_https_only(self) -> None:
        """Check that HTTPS-only is enabled for web services."""
        violations = []
        
        # Find web services
        for line_num, line in enumerate(self.lines, start=1):
            if re.search(r"Microsoft\.Web/(sites|apps)", line, re.IGNORECASE):
                resource_match = re.search(r"resource\s+(\w+)", line)
                resource_name = resource_match.group(1) if resource_match else "unknown"
                
                # Look ahead for httpsOnly setting
                found_https = False
                for offset in range(1, min(50, len(self.lines) - line_num + 1)):
                    check_line = self.lines[line_num - 1 + offset]
                    
                    if re.search(r"httpsOnly\s*:\s*true", check_line, re.IGNORECASE):
                        found_https = True
                        break
                    elif re.search(r"httpsOnly\s*:\s*false", check_line, re.IGNORECASE):
                        violations.append((line_num, resource_name))
                        break
                
                if not found_https and not any(v[1] == resource_name for v in violations):
                    violations.append((line_num, resource_name))
        
        if violations:
            messages = [f"Line {ln}: {rn}" for ln, rn in violations]
            self.results.append(ValidationResult(
                check_name="HTTPS Only",
                passed=False,
                message=f"Web services should have httpsOnly: true: {'; '.join(messages)}",
                severity="warning",
                line_number=violations[0][0],
                resource_name=violations[0][1]
            ))
        else:
            self.results.append(ValidationResult(
                check_name="HTTPS Only",
                passed=True,
                message="HTTPS-only configured for web services ✓",
                severity="info"
            ))
    
    def print_results(self, json_output: bool = False) -> None:
        """
        Print validation results.
        
        Args:
            json_output: Whether to output in JSON format
        """
        if json_output:
            output = {
                "file": str(self.bicep_file),
                "passed": all(r.passed for r in self.results if r.severity == "error"),
                "results": [asdict(r) for r in self.results]
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n🔍 Validating: {self.bicep_file}\n")
            print("=" * 80)
            
            errors = [r for r in self.results if not r.passed and r.severity == "error"]
            warnings = [r for r in self.results if not r.passed and r.severity == "warning"]
            passed = [r for r in self.results if r.passed]
            
            # Print errors
            if errors:
                print("\n❌ ERRORS:")
                for result in errors:
                    print(f"  • {result.check_name}: {result.message}")
            
            # Print warnings
            if warnings:
                print("\n⚠️  WARNINGS:")
                for result in warnings:
                    print(f"  • {result.check_name}: {result.message}")
            
            # Print passed checks (only in verbose mode)
            if self.verbose and passed:
                print("\n✅ PASSED:")
                for result in passed:
                    print(f"  • {result.check_name}: {result.message}")
            
            # Summary
            print("\n" + "=" * 80)
            total = len(self.results)
            error_count = len(errors)
            warning_count = len(warnings)
            pass_count = len(passed)
            
            if error_count == 0:
                print(f"\n✅ VALIDATION PASSED: {pass_count}/{total} checks passed, {warning_count} warnings")
            else:
                print(f"\n❌ VALIDATION FAILED: {error_count} errors, {warning_count} warnings, {pass_count} passed")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Bicep templates for SFI compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "bicep_file",
        type=Path,
        help="Path to Bicep template file to validate"
    )
    
    parser.add_argument(
        "--allow-front-door",
        action="store_true",
        help="Allow Azure Front Door resources (skip Front Door check)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed validation output"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    
    args = parser.parse_args()
    
    try:
        validator = BicepValidator(
            bicep_file=args.bicep_file,
            allow_front_door=args.allow_front_door,
            verbose=args.verbose
        )
        
        passed = validator.validate()
        validator.print_results(json_output=args.json)
        
        return 0 if passed else 1
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
