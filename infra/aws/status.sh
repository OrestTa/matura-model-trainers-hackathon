#!/usr/bin/env bash
# Shows running project instances, their projected cost to the deadline, and spend so far.
source "$(dirname "$0")/common.sh"
hours=$(hours_until_deadline)
total=0
echo -e "region\tid\ttype\tlaunched\tname"
while read -r r id t launched name; do
  [ -n "${id:-}" ] || continue
  echo -e "$r\t$id\t$t\t$launched\t$name"
  total=$(python3 -c "print($total + $(hourly_price "$t"))")
done < <(list_instances)
echo "Burn rate ~\$$total/h; projected to deadline ~\$$(python3 -c "print(round($total * $hours))") (cap \$$BUDGET_USD)"
echo "Month-to-date cost before credits: \$$(gross_cost_mtd)"
echo "Month-to-date cost after credits (would hit the card): \$$(net_cost_mtd) (limit \$$MAX_NET_USD)"
echo "(Cost Explorer lags several hours.)"
