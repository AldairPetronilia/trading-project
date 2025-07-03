package org.example.model.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum AreaType {
    BZN("Bidding Zone"),
    BZA("Bidding Zone Aggregation"),
    CTA("Control Area"),
    MBA("Market Balance Area"),
    IBA("Imbalance Area"),
    IPA("Imbalance Price Area"),
    LFA("Load Frequency Control Area"),
    LFB("Load Frequency Control Block"),
    REG("Region"),
    SCA("Scheduling Area"),
    SNA("Synchronous Area");

    private final String description;
}
