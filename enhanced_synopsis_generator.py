def generate_company_synopsis(data: Dict) -> Dict:
    """
    Generate intelligent company synopsis from existing GST data
    """
    synopsis = {
        'business_profile': {},
        'operational_insights': {},
        'compliance_summary': {},
        'risk_assessment': {}
    }
    
    # Business Profile
    company_name = data.get('lgnm', 'Unknown Company')
    trade_name = data.get('tradeName', '')
    registration_date = data.get('rgdt', '')
    company_type = data.get('ctb', '')
    status = data.get('sts', '')
    
    # Calculate business age
    business_age = calculate_business_age(registration_date)
    
    synopsis['business_profile'] = {
        'display_name': trade_name if trade_name and trade_name != company_name else company_name,
        'legal_name': company_name,
        'business_age': business_age,
        'entity_type': classify_entity_type(company_type),
        'operational_status': status,
        'state_code': data.get('gstin', '')[:2] if data.get('gstin') else '',
        'jurisdiction': data.get('stj', '')
    }
    
    # Operational Insights from Returns Data
    returns = data.get('returns', [])
    compliance = data.get('compliance', {})
    
    synopsis['operational_insights'] = {
        'filing_consistency': analyze_filing_pattern(returns),
        'recent_activity': get_recent_activity_status(returns),
        'return_types': get_return_types_summary(returns),
        'seasonal_patterns': detect_seasonal_patterns(returns)
    }
    
    # Compliance Summary
    synopsis['compliance_summary'] = {
        'overall_rating': compliance.get('grade', 'N/A'),
        'compliance_score': compliance.get('score', 0),
        'filing_reliability': assess_filing_reliability(returns),
        'penalty_risk': assess_penalty_risk(returns, compliance)
    }
    
    # Risk Assessment
    synopsis['risk_assessment'] = {
        'compliance_risk': calculate_compliance_risk(compliance, returns),
        'operational_risk': assess_operational_risk(data, returns),
        'red_flags': identify_red_flags(data, returns, compliance)
    }
    
    # Generate narrative summary
    synopsis['narrative'] = generate_narrative_summary(synopsis, data)
    
    return synopsis

def calculate_business_age(registration_date: str) -> str:
    """Calculate how long the business has been registered"""
    if not registration_date:
        return "Unknown"
    
    try:
        from datetime import datetime
        reg_date = datetime.strptime(registration_date, "%d/%m/%Y")
        age_days = (datetime.now() - reg_date).days
        years = age_days // 365
        months = (age_days % 365) // 30
        
        if years > 0:
            return f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months > 1 else ''}"
        else:
            return f"{months} month{'s' if months > 1 else ''}"
    except:
        return "Unknown"

def classify_entity_type(company_type: str) -> str:
    """Classify business entity type"""
    if not company_type:
        return "Unknown"
    
    type_map = {
        'Private Limited Company': 'Private Company',
        'Public Limited Company': 'Public Company',
        'Partnership': 'Partnership Firm',
        'Proprietorship': 'Sole Proprietorship',
        'LLP': 'Limited Liability Partnership',
        'Trust': 'Trust/Society',
        'Government': 'Government Entity'
    }
    
    for key, value in type_map.items():
        if key.lower() in company_type.lower():
            return value
    
    return company_type

def analyze_filing_pattern(returns: List[Dict]) -> str:
    """Analyze return filing consistency"""
    if not returns:
        return "No filing history"
    
    filed_returns = [r for r in returns if r.get('dof')]
    total_returns = len(returns)
    
    if not filed_returns:
        return "No returns filed"
    
    filing_rate = len(filed_returns) / total_returns
    
    if filing_rate >= 0.95:
        return "Highly consistent filer"
    elif filing_rate >= 0.8:
        return "Regular filer"
    elif filing_rate >= 0.6:
        return "Moderate filer"
    else:
        return "Irregular filer"

def get_recent_activity_status(returns: List[Dict]) -> str:
    """Get recent filing activity status"""
    if not returns:
        return "No recent activity"
    
    # Sort returns by financial year and tax period
    recent_returns = sorted(returns, key=lambda x: (x.get('fy', ''), x.get('taxp', '')), reverse=True)[:3]
    
    filed_recent = sum(1 for r in recent_returns if r.get('dof'))
    
    if filed_recent == len(recent_returns):
        return "Active and compliant"
    elif filed_recent > 0:
        return "Partially active"
    else:
        return "Inactive filing"

def get_return_types_summary(returns: List[Dict]) -> List[str]:
    """Get summary of return types filed"""
    if not returns:
        return []
    
    return_types = set()
    for ret in returns:
        ret_type = ret.get('rtype') or ret.get('rtntype', '')
        if ret_type:
            return_types.add(ret_type)
    
    return sorted(list(return_types))

def assess_filing_reliability(returns: List[Dict]) -> str:
    """Assess overall filing reliability"""
    if not returns:
        return "Unknown"
    
    late_returns = sum(1 for r in returns if r.get('late'))
    total_filed = sum(1 for r in returns if r.get('dof'))
    
    if total_filed == 0:
        return "No filing history"
    
    late_percentage = (late_returns / total_filed) * 100
    
    if late_percentage == 0:
        return "Always on time"
    elif late_percentage <= 10:
        return "Mostly on time" 
    elif late_percentage <= 25:
        return "Occasionally late"
    else:
        return "Frequently late"

def calculate_compliance_risk(compliance: Dict, returns: List[Dict]) -> str:
    """Calculate overall compliance risk level"""
    score = compliance.get('score', 0)
    
    if score >= 90:
        return "Low Risk"
    elif score >= 75:
        return "Medium Risk" 
    elif score >= 60:
        return "High Risk"
    else:
        return "Very High Risk"

def identify_red_flags(data: Dict, returns: List[Dict], compliance: Dict) -> List[str]:
    """Identify potential compliance red flags"""
    red_flags = []
    
    # Status check
    if data.get('sts', '').lower() == 'cancelled':
        red_flags.append("GST registration cancelled")
    
    # Low compliance score
    if compliance.get('score', 0) < 60:
        red_flags.append("Low compliance score")
    
    # High percentage of late returns
    late_returns = sum(1 for r in returns if r.get('late'))
    total_filed = sum(1 for r in returns if r.get('dof'))
    
    if total_filed > 0 and (late_returns / total_filed) > 0.3:
        red_flags.append("High rate of late filings")
    
    # No recent filings
    if returns:
        recent_returns = sorted(returns, key=lambda x: (x.get('fy', ''), x.get('taxp', '')), reverse=True)[:3]
        if not any(r.get('dof') for r in recent_returns):
            red_flags.append("No recent return filings")
    
    return red_flags

def generate_narrative_summary(synopsis: Dict, data: Dict) -> str:
    """Generate a human-readable narrative summary"""
    profile = synopsis['business_profile']
    insights = synopsis['operational_insights']
    compliance = synopsis['compliance_summary']
    
    company_name = profile['display_name']
    entity_type = profile['entity_type']
    business_age = profile['business_age']
    filing_pattern = insights['filing_consistency']
    compliance_grade = compliance['overall_rating']
    
    narrative = f"{company_name} is a {entity_type} operating for {business_age}. "
    narrative += f"The company is classified as a '{filing_pattern}' with an overall compliance grade of '{compliance_grade}'. "
    
    if insights['recent_activity'] == 'Active and compliant':
        narrative += "Recent filing activity shows good compliance discipline."
    elif insights['recent_activity'] == 'Inactive filing':
        narrative += "Recent filing activity shows concerning gaps in compliance."
    
    return narrative

# Additional helper functions for enhanced synopsis
def detect_seasonal_patterns(returns: List[Dict]) -> str:
    """Detect if there are seasonal filing patterns"""
    if len(returns) < 12:
        return "Insufficient data"
    
    # Group by months and analyze filing frequency
    monthly_filings = {}
    for ret in returns:
        if ret.get('dof'):
            try:
                month = ret['dof'].split('/')[1]  # Extract month from DD/MM/YYYY
                monthly_filings[month] = monthly_filings.get(month, 0) + 1
            except:
                continue
    
    if not monthly_filings:
        return "No pattern detected"
    
    # Simple pattern detection
    max_month = max(monthly_filings, key=monthly_filings.get)
    min_month = min(monthly_filings, key=monthly_filings.get)
    
    if monthly_filings[max_month] > monthly_filings[min_month] * 2:
        return f"Peak filing in month {max_month}"
    else:
        return "Consistent throughout year"

def assess_operational_risk(data: Dict, returns: List[Dict]) -> str:
    """Assess operational risk based on various factors"""
    risk_factors = []
    
    # Registration status
    if data.get('sts', '').lower() != 'active':
        risk_factors.append("Non-active status")
    
    # Filing gaps
    if returns:
        filed_count = sum(1 for r in returns if r.get('dof'))
        filing_rate = filed_count / len(returns)
        if filing_rate < 0.8:
            risk_factors.append("Inconsistent filing")
    
    # Determine overall risk
    if len(risk_factors) == 0:
        return "Low"
    elif len(risk_factors) <= 2:
        return "Medium"
    else:
        return "High"

def assess_penalty_risk(returns: List[Dict], compliance: Dict) -> str:
    """Assess risk of penalties based on late filings"""
    late_count = compliance.get('late_returns', 0)
    total_filed = compliance.get('filed_returns', 0)
    
    if total_filed == 0:
        return "Unknown"
    
    late_percentage = (late_count / total_filed) * 100
    
    if late_percentage == 0:
        return "Very Low"
    elif late_percentage <= 15:
        return "Low"
    elif late_percentage <= 30:
        return "Medium"
    else:
        return "High"