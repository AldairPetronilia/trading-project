package org.example.model.load;

import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.adapter.BusinessTypeAdapter;
import org.example.adapter.CurveTypeAdapter;
import org.example.adapter.ObjectAggregationAdapter;
import org.example.model.common.AreaCode;
import org.example.model.common.BusinessType;
import org.example.model.common.CurveType;
import org.example.model.common.DomainMRID;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;
import java.util.List;

// Enhanced LoadTimeSeries with ObjectAggregation enum
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class LoadTimeSeriesEnhanced {

    @XmlElement(name = "mRID")
    private String mRID;

    @XmlElement(name = "businessType")
    @XmlJavaTypeAdapter(BusinessTypeAdapter.class)
    private BusinessType businessType;

    @XmlElement(name = "objectAggregation")
    @XmlJavaTypeAdapter(ObjectAggregationAdapter.class)
    private ObjectAggregation objectAggregation;

    @XmlElement(name = "outBiddingZone_Domain.mRID")
    private DomainMRID outBiddingZoneDomainMRID;

    @XmlElement(name = "quantity_Measure_Unit.name")
    private String quantityMeasureUnitName;

    @XmlElement(name = "curveType")
    @XmlJavaTypeAdapter(CurveTypeAdapter.class)
    private CurveType curveType;

    @XmlElement(name = "Period")
    private List<LoadPeriod> periods;

    // Helper method to get area code
    public AreaCode getOutBiddingZoneAreaCode() {
        return outBiddingZoneDomainMRID != null ? outBiddingZoneDomainMRID.getAreaCode() : null;
    }
}
