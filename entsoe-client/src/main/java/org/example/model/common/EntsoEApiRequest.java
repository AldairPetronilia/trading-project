package org.example.model.common;

import lombok.Builder;
import lombok.Data;
import lombok.NonNull;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * Base request parameters for ENTSO-E API calls
 */
@Data
@Builder
public class EntsoEApiRequest {

    @NonNull
    private DocumentType documentType;

    private ProcessType processType;
    private BusinessType businessType;
    private PsrType psrType;
    private DocStatus docStatus;

    // Domain parameters using type-safe AreaCode enums
    private AreaCode outBiddingZoneDomain;
    private AreaCode biddingZoneDomain;
    private AreaCode controlAreaDomain;
    private AreaCode inDomain;
    private AreaCode outDomain;
    private AreaCode acquiringDomain;
    private AreaCode connectingDomain;
    private AreaCode areaDomain;

    @NonNull
    private LocalDateTime periodStart;

    @NonNull
    private LocalDateTime periodEnd;

    private LocalDateTime periodStartUpdate;
    private LocalDateTime periodEndUpdate;

    // Other parameters
    private String registeredResource;
    private ContractMarketAgreementType contractMarketAgreementType;
    private ContractMarketAgreementType typeMarketAgreementType;
    private AuctionType auctionType;
    private AuctionCategory auctionCategory;
    private String classificationSequencePosition;
    private String standardMarketProduct;
    private String originalMarketProduct;
    private Direction direction;
    private String mRID;
    private Integer offset;
    private String implementationDateAndOrTime;
    private String updateDateAndOrTime;

    /**
     * Converts the request parameters to a map suitable for HTTP requests
     * Uses proper ENTSO-E codes from enums
     */
    public Map<String, String> toParameterMap() {
        Map<String, String> params = new HashMap<>();

        // Required parameters - use getCode() for proper ENTSO-E codes
        params.put("documentType", documentType.getCode());

        params.put("periodStart", formatDateTime(periodStart));

        params.put("periodEnd", formatDateTime(periodEnd));

        // Optional parameters with proper ENTSO-E codes
        addEnumIfNotNull(params, "processType", processType);
        addEnumIfNotNull(params, "businessType", businessType);
        addEnumIfNotNull(params, "psrType", psrType);
        addEnumIfNotNull(params, "docStatus", docStatus);

        // Domain parameters using AreaCode enums
        addAreaCodeIfNotNull(params, "outBiddingZone_Domain", outBiddingZoneDomain);
        addAreaCodeIfNotNull(params, "biddingZone_Domain", biddingZoneDomain);
        addAreaCodeIfNotNull(params, "controlArea_Domain", controlAreaDomain);
        addAreaCodeIfNotNull(params, "in_Domain", inDomain);
        addAreaCodeIfNotNull(params, "out_Domain", outDomain);
        addAreaCodeIfNotNull(params, "acquiring_Domain", acquiringDomain);
        addAreaCodeIfNotNull(params, "connecting_Domain", connectingDomain);
        addAreaCodeIfNotNull(params, "area_Domain", areaDomain);

        // Time update parameters
        if (periodStartUpdate != null) {
            params.put("periodStartUpdate", formatDateTime(periodStartUpdate));
        }
        if (periodEndUpdate != null) {
            params.put("periodEndUpdate", formatDateTime(periodEndUpdate));
        }

        // Other parameters
        addIfNotNull(params, "registeredResource", registeredResource);
        addEnumIfNotNull(params, "contract_MarketAgreement.Type", contractMarketAgreementType);
        addEnumIfNotNull(params, "type_MarketAgreement.Type", typeMarketAgreementType);
        addEnumIfNotNull(params, "auction.Type", auctionType);
        addEnumIfNotNull(params, "auction.Category", auctionCategory);
        addIfNotNull(params, "classificationSequence_AttributeInstanceComponent.Position", classificationSequencePosition);
        addIfNotNull(params, "standard_MarketProduct", standardMarketProduct);
        addIfNotNull(params, "original_MarketProduct", originalMarketProduct);
        addEnumIfNotNull(params, "direction", direction);
        addIfNotNull(params, "mRID", mRID);
        addIfNotNull(params, "implementation_DateAndOrTime", implementationDateAndOrTime);
        addIfNotNull(params, "update_DateAndOrTime", updateDateAndOrTime);

        if (offset != null) {
            params.put("offset", offset.toString());
        }

        return params;
    }

    private void addEnumIfNotNull(Map<String, String> params, String key, Object enumValue) {
        if (enumValue != null) {
            try {
                // Use reflection to call getCode() method on our custom enums
                String code = (String) enumValue.getClass().getMethod("getCode").invoke(enumValue);
                params.put(key, code);
            } catch (Exception e) {
                // Fallback to enum name if getCode() method not found
                params.put(key, ((Enum<?>) enumValue).name());
            }
        }
    }


    private void addAreaCodeIfNotNull(Map<String, String> params, String key, AreaCode areaCode) {
        if (areaCode != null) {
            params.put(key, areaCode.getCode());
        }
    }

    private void addIfNotNull(Map<String, String> params, String key, Object value) {
        if (value != null) {
            params.put(key, value.toString());
        }
    }

    private String formatDateTime(LocalDateTime dateTime) {
        return dateTime.format(DateTimeFormatter.ofPattern("yyyyMMddHHmm"));
    }

    /**
     * Validates domain parameters against their supported area types
     */
    public void validateDomainParameters() {
        validateAreaType(biddingZoneDomain, AreaType.BZN, "biddingZoneDomain");
        validateAreaType(controlAreaDomain, AreaType.CTA, "controlAreaDomain");
        validateAreaType(outBiddingZoneDomain, AreaType.BZN, "outBiddingZoneDomain");
    }

    private void validateAreaType(AreaCode areaCode, AreaType requiredType, String parameterName) {
        if (areaCode != null && !areaCode.hasAreaType(requiredType)) {
            throw new IllegalArgumentException(
                    String.format("Area %s (%s) does not support %s. Supported types: %s",
                            areaCode.getDescription(), areaCode.getCode(),
                            requiredType.getDescription(), areaCode.getAreaTypesList())
            );
        }
    }
}
