package org.example.model.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Arrays;

@Getter
@AllArgsConstructor
public enum AuctionType {
    IMPLICIT("A01", "Implicit"),
    EXPLICIT("A02", "Explicit");

    private final String code;
    private final String description;

    public static AuctionType fromCode(String code) {
        return Arrays.stream(values())
                .filter(type -> type.code.equals(code))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown AuctionType code: " + code));
    }
}
