package org.example.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Arrays;

@Getter
@AllArgsConstructor
public enum AuctionCategory {
    BASE("A01", "Base"),
    PEAK("A02", "Peak"),
    OFF_PEAK("A03", "Off Peak"),
    HOURLY("A04", "Hourly");

    private final String code;
    private final String description;

    public static AuctionCategory fromCode(String code) {
        return Arrays.stream(values())
                .filter(type -> type.code.equals(code))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown AuctionCategory code: " + code));
    }
}
