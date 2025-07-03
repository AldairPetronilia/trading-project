package org.example.api;

import lombok.Builder;
import lombok.Data;
import lombok.NonNull;
import org.example.model.common.*;

import java.time.LocalDateTime;

/**
 * Specialized builder for ENTSO-E Load Domain API endpoints
 * Supports all load-related data types with predefined configurations
 */
@Data
@Builder
public class LoadDomainRequestBuilder {

    @NonNull
    private AreaCode outBiddingZoneDomain;

    @NonNull
    private LocalDateTime periodStart;

    @NonNull
    private LocalDateTime periodEnd;

    // Optional parameters
    private String timeInterval;
    private Integer offset;

    /**
     * Creates request for Actual Total Load [6.1.A]
     * One year range limit, minimum MTU period resolution
     */
    public static LoadDomainRequestBuilder actualTotalLoad() {
        return LoadDomainRequestBuilder.builder().build();
    }

    /**
     * Creates request for Day-Ahead Total Load Forecast [6.1.B]
     * One year range limit, minimum one day resolution
     */
    public static LoadDomainRequestBuilder dayAheadLoadForecast() {
        return LoadDomainRequestBuilder.builder().build();
    }

    /**
     * Creates request for Week-Ahead Total Load Forecast [6.1.C]
     * One year range limit, minimum one week resolution
     */
    public static LoadDomainRequestBuilder weekAheadLoadForecast() {
        return LoadDomainRequestBuilder.builder().build();
    }

    /**
     * Creates request for Month-Ahead Total Load Forecast [6.1.D]
     * One year range limit, minimum one month resolution
     */
    public static LoadDomainRequestBuilder monthAheadLoadForecast() {
        return LoadDomainRequestBuilder.builder().build();
    }

    /**
     * Creates request for Year-Ahead Total Load Forecast [6.1.E]
     * One year range limit, minimum one year resolution
     */
    public static LoadDomainRequestBuilder yearAheadLoadForecast() {
        return LoadDomainRequestBuilder.builder().build();
    }

    /**
     * Creates request for Year-Ahead Forecast Margin [8.1]
     * One year range limit, minimum one year resolution
     */
    public static LoadDomainRequestBuilder yearAheadForecastMargin() {
        return LoadDomainRequestBuilder.builder().build();
    }

    // Fluent builder methods
    public LoadDomainRequestBuilder forBiddingZone(AreaCode biddingZone) {
        validateBiddingZone(biddingZone);
        this.outBiddingZoneDomain = biddingZone;
        return this;
    }

    public LoadDomainRequestBuilder fromPeriod(LocalDateTime start, LocalDateTime end) {
        validateDateRange(start, end);
        this.periodStart = start;
        this.periodEnd = end;
        return this;
    }

    public LoadDomainRequestBuilder withTimeInterval(String timeInterval) {
        this.timeInterval = timeInterval;
        return this;
    }

    public LoadDomainRequestBuilder withOffset(Integer offset) {
        this.offset = offset;
        return this;
    }

    /**
     * Builds EntsoEApiRequest for Actual Total Load [6.1.A]
     */
    public EntsoEApiRequest buildActualTotalLoad() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.REALISED)                 // A16
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Day-Ahead Total Load Forecast [6.1.B]
     */
    public EntsoEApiRequest buildDayAheadLoadForecast() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.DAY_AHEAD)                // A01
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Week-Ahead Total Load Forecast [6.1.C]
     */
    public EntsoEApiRequest buildWeekAheadLoadForecast() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.WEEK_AHEAD)               // A31
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Month-Ahead Total Load Forecast [6.1.D]
     */
    public EntsoEApiRequest buildMonthAheadLoadForecast() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.MONTH_AHEAD)              // A32
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Year-Ahead Total Load Forecast [6.1.E]
     */
    public EntsoEApiRequest buildYearAheadLoadForecast() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.SYSTEM_TOTAL_LOAD)      // A65
                .processType(ProcessType.YEAR_AHEAD)               // A33
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    /**
     * Builds EntsoEApiRequest for Year-Ahead Forecast Margin [8.1]
     */
    public EntsoEApiRequest buildYearAheadForecastMargin() {
        return EntsoEApiRequest.builder()
                .documentType(DocumentType.LOAD_FORECAST_MARGIN)   // A70
                .processType(ProcessType.YEAR_AHEAD)               // A33
                .outBiddingZoneDomain(outBiddingZoneDomain)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .offset(offset)
                .build();
    }

    // Validation methods
    private void validateBiddingZone(AreaCode areaCode) {
        if (areaCode != null && !areaCode.hasAreaType(AreaType.BZN)) {
            throw new IllegalArgumentException(
                    String.format("Area %s (%s) is not a valid bidding zone. Supported types: %s",
                            areaCode.getDescription(), areaCode.getCode(), areaCode.getAreaTypesList())
            );
        }
    }

    private void validateDateRange(LocalDateTime start, LocalDateTime end) {
        if (start != null && end != null) {
            if (start.isAfter(end)) {
                throw new IllegalArgumentException("Period start must be before period end");
            }

            // Check one year limit
            if (start.plusYears(1).isBefore(end)) {
                throw new IllegalArgumentException("Date range cannot exceed one year");
            }
        }
    }
}
