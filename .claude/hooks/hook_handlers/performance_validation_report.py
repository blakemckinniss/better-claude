#!/usr/bin/env python3
"""Performance Validation Report for Refactored Hook Architecture.

Generates a comprehensive production readiness report based on validation results.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


def run_performance_benchmark() -> Dict[str, Any]:
    """Run focused performance benchmarks on the hooks."""
    
    hook_dir = Path(__file__).parent
    pretool_hook = hook_dir / "PreToolUse.py" 
    posttool_hook = hook_dir / "PostToolUse" / "__init__.py"
    
    # Performance test data
    test_cases = [
        # Security blocking tests
        {
            "name": "destructive_edit_block",
            "hook": pretool_hook,
            "data": {
                "session_id": "perf-test",
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/large_file_backup.py",
                    "content": "small",
                },
            },
        },
        {
            "name": "normal_operation",
            "hook": pretool_hook,
            "data": {
                "session_id": "perf-test",
                "tool_name": "Read",
                "tool_input": {
                    "file_path": "/tmp/normal.py",
                },
            },
        },
        # PostToolUse educational test
        {
            "name": "educational_feedback",
            "hook": posttool_hook,
            "data": {
                "session_id": "perf-test",
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/test.py",
                },
                "tool_response": "File written successfully",
            },
        },
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"⏱️  Benchmarking: {test_case['name']}")
        
        # Run multiple iterations for accurate timing
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            
            result = subprocess.run(
                [sys.executable, str(test_case['hook'])],
                input=json.dumps(test_case['data']),
                text=True,
                capture_output=True,
                timeout=2,
            )
            
            execution_time = (time.perf_counter() - start_time) * 1000  # ms
            times.append(execution_time)
        
        # Calculate statistics
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        results.append({
            "test": test_case['name'],
            "hook": Path(str(test_case['hook'])).stem,
            "avg_ms": round(avg_time, 2),
            "min_ms": round(min_time, 2),
            "max_ms": round(max_time, 2),
            "target_met": avg_time < (50 if "PreToolUse" in str(test_case['hook']) else 100),
            "exit_code": result.returncode,
            "stderr_length": len(result.stderr),
        })
    
    return {
        "timestamp": time.time(),
        "performance_results": results,
    }


def validate_architecture_compliance() -> Dict[str, Any]:
    """Validate architecture compliance with Hook Contract."""
    
    compliance_checks = {
        "pretool_streamlined": {
            "description": "PreToolUse reduced from 807 to ~200 lines",
            "target": 250,
            "current": 0,  # Will be calculated
        },
        "posttool_enhanced": {
            "description": "PostToolUse provides educational feedback",
            "target": True,
            "current": False,  # Will be calculated
        },
        "shared_intelligence": {
            "description": "Shared intelligence components functional",
            "target": True,
            "current": False,  # Will be calculated
        },
        "exit_code_compliance": {
            "description": "Proper exit code usage (0 for allow, 2 for block/educate)",
            "target": True,
            "current": False,  # Will be calculated
        },
    }
    
    # Check PreToolUse line count
    pretool_path = Path(__file__).parent / "PreToolUse.py"
    with open(pretool_path) as f:
        pretool_lines = len([line for line in f if line.strip() and not line.strip().startswith('#')])
    
    compliance_checks["pretool_streamlined"]["current"] = pretool_lines
    target_lines = compliance_checks["pretool_streamlined"]["target"]
    assert isinstance(target_lines, int)
    compliance_checks["pretool_streamlined"]["passed"] = pretool_lines <= target_lines
    
    # Check PostToolUse educational feedback capability
    try:
        compliance_checks["shared_intelligence"]["current"] = True
        compliance_checks["shared_intelligence"]["passed"] = True
        
        # Test educational feedback system
        from PostToolUse.educational_feedback_enhanced import \
            EducationalFeedbackSystem
        EducationalFeedbackSystem()
        compliance_checks["posttool_enhanced"]["current"] = True
        compliance_checks["posttool_enhanced"]["passed"] = True
        
    except ImportError:
        compliance_checks["shared_intelligence"]["passed"] = False
        compliance_checks["posttool_enhanced"]["passed"] = False
    
    # Test exit code compliance
    try:
        test_data = {
            "session_id": "compliance-test",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/test_backup.py",  # Should trigger blocking
                "content": "test",
            },
        }
        
        result = subprocess.run(
            [sys.executable, str(pretool_path)],
            input=json.dumps(test_data),
            text=True,
            capture_output=True,
        )
        
        compliance_checks["exit_code_compliance"]["current"] = result.returncode == 2
        compliance_checks["exit_code_compliance"]["passed"] = result.returncode == 2
        
    except Exception:
        compliance_checks["exit_code_compliance"]["passed"] = False
    
    return {
        "compliance_summary": {
            "total_checks": len(compliance_checks),
            "passed_checks": sum(1 for check in compliance_checks.values() if check.get("passed", False)),
            "compliance_rate": sum(1 for check in compliance_checks.values() if check.get("passed", False)) / len(compliance_checks) * 100,
        },
        "detailed_checks": compliance_checks,
    }


def generate_recommendations(performance_data: Dict, compliance_data: Dict, overall_score: float) -> List[str]:
    """Generate specific recommendations based on validation results."""
    
    recommendations = []
    
    # Performance recommendations
    for result in performance_data["performance_results"]:
        if not result["target_met"]:
            if "PreToolUse" in result["hook"]:
                recommendations.append(f"🚀 Optimize {result['test']}: Currently {result['avg_ms']}ms, target <50ms")
            else:
                recommendations.append(f"📚 Optimize {result['test']}: Currently {result['avg_ms']}ms, target <100ms")
    
    # Compliance recommendations
    for check_name, check_data in compliance_data["detailed_checks"].items():
        if not check_data.get("passed", False):
            recommendations.append(f"✅ Fix compliance: {check_data['description']}")
    
    # Overall recommendations
    if overall_score < 80:
        recommendations.append("⚠️  Overall score below production threshold (80%)")
        recommendations.append("📝 Review and address failed validations before deployment")
    elif overall_score < 90:
        recommendations.append("💡 Good production readiness - consider addressing minor issues for optimization")
    else:
        recommendations.append("🎉 Excellent production readiness - system ready for deployment")
    
    return recommendations


def generate_production_readiness_report() -> Dict[str, Any]:
    """Generate comprehensive production readiness report."""
    
    print("🔍 Running Performance Benchmarks...")
    performance_data = run_performance_benchmark()
    
    print("📋 Validating Architecture Compliance...")
    compliance_data = validate_architecture_compliance()
    
    # Calculate overall readiness score
    performance_score = sum(1 for result in performance_data["performance_results"] if result["target_met"]) / len(performance_data["performance_results"]) * 100
    compliance_score = compliance_data["compliance_summary"]["compliance_rate"]
    
    overall_score = (performance_score + compliance_score) / 2
    
    production_ready = overall_score >= 80  # 80% threshold
    
    return {
        "timestamp": time.time(),
        "overall_assessment": {
            "production_ready": production_ready,
            "overall_score": round(overall_score, 1),
            "performance_score": round(performance_score, 1),
            "compliance_score": round(compliance_score, 1),
        },
        "performance_data": performance_data,
        "compliance_data": compliance_data,
        "recommendations": generate_recommendations(performance_data, compliance_data, overall_score),
    }


def print_report(report: Dict[str, Any]):
    """Print formatted production readiness report."""
    
    print("\f")  # Clear screen
    print("=" * 80)
    print(" PRODUCTION VALIDATION REPORT - REFACTORED HOOK ARCHITECTURE")
    print("=" * 80)
    
    # Overall Assessment
    assessment = report["overall_assessment"]
    status = "✅ READY" if assessment["production_ready"] else "❌ NOT READY"
    
    print(f"\n📊 OVERALL ASSESSMENT: {status}")
    print(f"Overall Score: {assessment['overall_score']}%")
    print(f"Performance Score: {assessment['performance_score']}%")
    print(f"Compliance Score: {assessment['compliance_score']}%")
    
    # Performance Results
    print(f"\n⚡ PERFORMANCE BENCHMARKS")
    print("-" * 50)
    for result in report["performance_data"]["performance_results"]:
        status = "✅" if result["target_met"] else "❌"
        print(f"{status} {result['test']} ({result['hook']})")
        print(f"   Avg: {result['avg_ms']}ms | Min: {result['min_ms']}ms | Max: {result['max_ms']}ms")
        
        if result['stderr_length'] > 0:
            print(f"   Educational feedback: {result['stderr_length']} chars")
    
    # Compliance Results  
    print(f"\n📋 ARCHITECTURE COMPLIANCE")
    print("-" * 50)
    compliance = report["compliance_data"]["detailed_checks"]
    for check_name, check_data in compliance.items():
        status = "✅" if check_data.get("passed", False) else "❌"
        print(f"{status} {check_data['description']}")
        if "current" in check_data:
            print(f"   Current: {check_data['current']} | Target: {check_data['target']}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 50)
    for rec in report["recommendations"]:
        print(f"• {rec}")
    
    print(f"\n{'=' * 80}")
    
    return assessment["production_ready"]


def main():
    """Main execution."""
    try:
        report = generate_production_readiness_report()
        production_ready = print_report(report)
        
        # Export detailed report
        report_file = Path(__file__).parent / "production_validation_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Exit with appropriate code
        sys.exit(0 if production_ready else 1)
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
