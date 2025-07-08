package org.example.model.common;

import java.util.Arrays;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum MarketRoleType {
  ISSUING_OFFICE("A32", "Issuing Office"),
  MARKET_OPERATOR("A33", "Market Operator");

  private final String code;
  private final String description;

  public static MarketRoleType fromCode(String code) {
    return Arrays.stream(values())
        .filter(type -> type.code.equals(code))
        .findFirst()
        .orElseThrow(() -> new IllegalArgumentException("Unknown MarketRoleType code: " + code));
  }
}
