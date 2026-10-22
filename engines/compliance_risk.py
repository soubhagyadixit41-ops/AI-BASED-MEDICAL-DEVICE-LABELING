
def check_label(label):
    required_fields = [
        "product_name",
        "manufacturer",
        "intended_use"
    ]

    findings = []

    for field in required_fields:
        value = label.get(field, "")

        if not isinstance(value, str) or not value.strip():
            findings.append({
                "field": field,
                "risk": "HIGH",
                "finding": f"Missing field: {field}"
            })

    return findings, len(required_fields)


def generate_report(label, label_name):
    findings, total_checks = check_label(label)

    print("\n" + "=" * 48)
    print("       LABELGUARD AI")
    print("       COMPLIANCE RISK REPORT")
    print("=" * 48)
    print(f"Label       : {label_name}")
    print(f"Checks      : {total_checks}")
    print(f"Findings    : {len(findings)}")

    if findings:
        print("Status      : REVIEW REQUIRED")
        print("\nDETECTED ISSUES")
        for item in findings:
            print(f"  [{item['risk']}] {item['finding']}")
    else:
        print("Status      : NO MISSING FIELDS")
        print("All demo-required fields are present.")

    print("=" * 48)


if __name__ == "__main__":
    incomplete_label = {
        "product_name": "Device X100",
        "manufacturer": "",
        "intended_use": "Demo intended use"
    }

    complete_label = {
        "product_name": "Device X100",
        "manufacturer": "Example Medical Ltd.",
        "intended_use": "Demo intended use"
    }

    generate_report(incomplete_label, "Test A - Incomplete")
    generate_report(complete_label, "Test B - Complete")
