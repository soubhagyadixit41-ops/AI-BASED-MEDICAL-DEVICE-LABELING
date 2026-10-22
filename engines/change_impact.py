
import pandas as pd

def find_affected_labels(change, labels):
    changed_field = change["changed_field"]
    target_product = change["product"]
    results = []

    for _, label in labels.iterrows():
        fields = label["dependent_fields"].split(";")

        # Check whether the field and product match
        if (
            changed_field in fields
            and label["product"] == target_product
        ):
            results.append({
                "Label ID": label["label_id"],
                "Product": label["product"],
                "Market": label["market"],
                "Language": label["language"],
                "Impact": "HIGH",
                "Required Action": "Review and update label"
            })

    return pd.DataFrame(results)


if __name__ == "__main__":
    labels = pd.read_csv("data/labels.csv")

    change = {
        "change_id": "CR-001",
        "product": "Device X100",
        "changed_field": "manufacturer_address"
    }

    affected = find_affected_labels(change, labels)

    print("\nSMART CHANGE IMPACT ANALYSIS")
    print("=" * 50)
    print("Change Request:", change["change_id"])
    print("Product:", change["product"])
    print("Changed Field:", change["changed_field"])
    print("Affected Labels:", len(affected))
    print("\nImpact Report:")

    if not affected.empty:
        print(affected.to_string(index=False))
    else:
        print("No affected labels found.")
