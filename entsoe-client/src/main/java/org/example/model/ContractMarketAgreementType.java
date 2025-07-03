package org.example.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Arrays;

@Getter
@AllArgsConstructor
public enum ContractMarketAgreementType {
    DAILY("A01", "Daily"),
    WEEKLY("A02", "Weekly"),
    MONTHLY("A03", "Monthly"),
    YEARLY("A04", "Yearly"),
    TOTAL("A05", "Total"),
    LONG_TERM("A06", "Long term"),
    INTRADAY("A07", "Intraday"),
    HOURLY("A13", "Hourly");

    private final String code;
    private final String description;

    public static ContractMarketAgreementType fromCode(String code) {
        return Arrays.stream(values())
                .filter(type -> type.code.equals(code))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown ContractMarketAgreementType code: " + code));
    }
}
