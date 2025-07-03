package org.example.model.load;

import lombok.Data;
import lombok.NoArgsConstructor;
import org.example.adapter.BusinessTypeAdapter;
import org.example.adapter.CurveTypeAdapter;
import org.example.model.common.BusinessType;
import org.example.model.common.CurveType;
import org.example.model.common.DomainMRID;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.adapters.XmlJavaTypeAdapter;
import java.util.List;

// Time Series class specific for Load Domain
@XmlAccessorType(XmlAccessType.FIELD)
@Data
@NoArgsConstructor
public class LoadTimeSeries {

    @XmlElement(name = "mRID")
    private String mRID;

    @XmlElement(name = "businessType")
    @XmlJavaTypeAdapter(BusinessTypeAdapter.class)
    private BusinessType businessType;

    @XmlElement(name = "objectAggregation")
    private String objectAggregation;

    @XmlElement(name = "outBiddingZone_Domain.mRID")
    private DomainMRID outBiddingZoneDomainMRID;

    @XmlElement(name = "quantity_Measure_Unit.name")
    private String quantityMeasureUnitName;

    @XmlElement(name = "curveType")
    @XmlJavaTypeAdapter(CurveTypeAdapter.class)
    private CurveType curveType;

    @XmlElement(name = "Period")
    private List<LoadPeriod> periods;
}
