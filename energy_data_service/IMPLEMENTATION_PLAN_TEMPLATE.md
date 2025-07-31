# Implementation Plan Template

## Guidelines for Using This Template

This template provides a structured approach for creating comprehensive implementation plans. Replace all `[PLACEHOLDER]` sections with specific details for your implementation step.

---

# Current Implementation Plan - [LAYER/FEATURE NAME]

## Next Atomic Step: [STEP NAME]

Based on the completed [PREVIOUS LAYER/FEATURE], the next step is implementing [BRIEF DESCRIPTION OF WHAT YOU'RE BUILDING].

### What to implement next:

1. **[Component 1 Name]** (`[file/path]`)
   - [Key feature or responsibility 1]
   - [Key feature or responsibility 2]
   - [Key feature or responsibility 3]
   - [Key feature or responsibility 4]

2. **[Component 2 Name]** (`[file/path]`)
   - [Key feature or responsibility 1]
   - [Key feature or responsibility 2]
   - [Key feature or responsibility 3]
   - [Key feature or responsibility 4]

3. **[Component 3 Name]** (`[file/path]`)
   - [Key feature or responsibility 1]
   - [Key feature or responsibility 2]
   - [Key feature or responsibility 3]
   - [Key feature or responsibility 4]

4. **[Component 4 Name]** (`[file/path]`) *(if applicable)*
   - [Key feature or responsibility 1]
   - [Key feature or responsibility 2]
   - [Key feature or responsibility 3]

### Implementation Requirements:

#### [Component 1 Name] Features:
- **[Feature category 1]**: [Detailed requirement description]
- **[Feature category 2]**: [Detailed requirement description]
- **[Feature category 3]**: [Detailed requirement description]
- **[Feature category 4]**: [Detailed requirement description]
- **[Feature category 5]**: [Detailed requirement description]
- **[Feature category 6]**: [Detailed requirement description]

#### [Component 2 Name] Features:
- [Requirement with brief description]
- [Requirement with brief description]
- [Requirement with brief description]
- [Requirement with brief description]
- [Requirement with brief description]
- [Requirement with brief description]

#### [Component 3 Name] Features:
- **[Feature category 1]**: [Detailed requirement description]
- **[Feature category 2]**: [Detailed requirement description]
- **[Feature category 3]**: [Detailed requirement description]
- **[Feature category 4]**: [Detailed requirement description]
- **[Feature category 5]**: [Detailed requirement description]
- **[Feature category 6]**: [Detailed requirement description]

### Test Coverage Requirements:

1. **[Test Suite 1 Name]** (`[test/file/path]`)
   - [Test requirement 1]
   - [Test requirement 2]
   - [Test requirement 3]
   - [Test requirement 4]

2. **[Test Suite 2 Name]** (`[test/file/path]`)
   - [Test requirement 1]
   - [Test requirement 2]
   - [Test requirement 3]
   - [Test requirement 4]

3. **[Test Suite 3 Name]** (`[test/file/path]`)
   - [Test requirement 1]
   - [Test requirement 2]
   - [Test requirement 3]
   - [Test requirement 4]

4. **[Integration Test Suite 1]** (`[test/file/path]`)
   - [Integration test requirement 1]
   - [Integration test requirement 2]
   - [Integration test requirement 3]
   - [Integration test requirement 4]

5. **[Integration Test Suite 2]** (`[test/file/path]`) *(if applicable)*
   - [Integration test requirement 1]
   - [Integration test requirement 2]
   - [Integration test requirement 3]

### Dependencies:

- Builds on existing [Component/Class] from `[file/path]`
- Uses [Component/Configuration] from `[file/path]`
- Uses [Model/Class] from `[file/path]`
- Requires [Library/Package] (already in pyproject.toml / needs to be added)
- Integration with [existing system/pattern]
- [Future integration requirement] for [next layer/feature]

### Success Criteria:

- **[Primary Success Metric]**: [Detailed description of what success looks like]
- **[Testing Success Metric]**: [What comprehensive coverage means]
- **[Integration Success Metric]**: [How components work together]
- **[Performance Success Metric]**: [Performance requirements if applicable]
- **[Error Handling Success Metric]**: [Error handling requirements]
- **[Code Quality Success Metric]**: Passes all checks (ruff, mypy, pre-commit)
- **[Architecture Success Metric]**: [How this prepares for next steps]
- **[Pattern Consistency Success Metric]**: [How this follows existing patterns]

This [BRIEF DESCRIPTION OF PURPOSE] establishes [WHAT FOUNDATION/CAPABILITY IT PROVIDES] needed for [NEXT STEPS/FUTURE FEATURES].

---

## Further Implementation Details

### 🔍 **[Problem/Technical Debt Analysis Section]**

#### **[Root Cause/Current Issues]:**
[Detailed analysis of what problem this implementation solves. Include:]
- Current technical debt or architectural issues
- Specific code locations with problems (file:line references)
- Performance bottlenecks or inefficiencies
- Pattern inconsistencies or violations

**[Current Problematic Code Example]:**
```python
# ❌ WRONG: [Description of what's wrong]
[current_code_example]
```

**[Why This is Technical Debt/Problem]:**
1. **[Issue 1]**: [Detailed explanation]
2. **[Issue 2]**: [Detailed explanation]
3. **[Issue 3]**: [Detailed explanation]

### 🛠️ **[Detailed Implementation Strategy Section]**

#### **[Core Solution Approach]:**
[Explain the approach to solving the problem. Include:]

**[New Pattern/Solution]:**
```python
# ✅ CORRECT: [Description of the solution]
[solution_code_example]
```

#### **[Detailed Component Implementation]:**

**[Component 1 Implementation Details]:**
```python
# [Component 1 implementation example with key methods]
class [ComponentName]:
    [method_examples_with_explanations]
```

**[Component 2 Implementation Details]:**
```python
# [Component 2 implementation example]
[detailed_code_examples]
```

### 🔄 **[Before/After Transformation Section]**

#### **Before ([Current Implementation]):**
```python
# ❌ [Current problematic pattern]
[before_code_example_with_detailed_comments_on_issues]
```

#### **After ([New Clean Implementation]):**
```python
# ✅ [New clean pattern]
[after_code_example_with_detailed_comments_on_improvements]
```

### 📊 **[Benefits Quantification Section]**

#### **[Performance Improvements]:**
- **[Metric 1]**: [Specific improvement with percentage/numbers]
- **[Metric 2]**: [Specific improvement with percentage/numbers]
- **[Metric 3]**: [Specific improvement with percentage/numbers]

#### **[Code Quality Improvements]:**
- **[Quality Aspect 1]**: [Detailed explanation of improvement]
- **[Quality Aspect 2]**: [Detailed explanation of improvement]
- **[Quality Aspect 3]**: [Detailed explanation of improvement]

#### **[Architectural Improvements]:**
- **[Architecture Aspect 1]**: [How it improves architecture]
- **[Architecture Aspect 2]**: [How it improves architecture]
- **[Architecture Aspect 3]**: [How it improves architecture]

### 🧪 **[Comprehensive Testing Strategy Section]**

#### **[Unit Tests Details]:**
```python
# [Detailed test examples]
class Test[ComponentName]:
    async def test_[specific_functionality](self):
        # [Test implementation example]

    async def test_[edge_case_or_error_scenario](self):
        # [Test implementation example]
```

#### **[Integration Tests Details]:**
```python
# [Integration test examples]
class Test[ComponentName]Integration:
    async def test_[end_to_end_scenario](self):
        # [Integration test example]
```

#### **[Performance/Load Tests]:**
- **[Performance Test 1]**: [Description and expected results]
- **[Performance Test 2]**: [Description and expected results]

### 🎯 **[Migration/Rollout Strategy Section]**

#### **[Implementation Phases]:**
1. **[Phase 1]**: [What gets implemented first and why]
2. **[Phase 2]**: [What gets implemented second and why]
3. **[Phase 3]**: [What gets implemented last and why]

#### **[Backwards Compatibility]:**
- **[Compatibility Concern 1]**: [How it's addressed]
- **[Compatibility Concern 2]**: [How it's addressed]

#### **[Risk Mitigation]:**
- **[Risk 1]**: [Mitigation strategy]
- **[Risk 2]**: [Mitigation strategy]

---

## Template Usage Notes

### Section Guidelines:

**Title Structure**: Use format "Current Implementation Plan - [LAYER/FEATURE NAME]"

**Next Atomic Step**: Should be concise but descriptive of the main goal

**What to implement next**:
- List 2-4 concrete components with file paths
- Use bullet points for key responsibilities (3-4 per component)
- Order by implementation sequence if dependencies exist

**Implementation Requirements**:
- Group by component with clear sub-headers
- Use **bold categories** for major feature groups
- Be specific about technical requirements
- Include performance, error handling, and integration requirements

**Test Coverage Requirements**:
- Include both unit and integration tests
- Specify test file paths following project conventions
- Cover all major functionality and edge cases
- Include performance and concurrency testing when relevant

**Dependencies**:
- List existing components this builds upon
- Specify new dependencies needed
- Note integration points with other systems
- Include future integration requirements

**Success Criteria**:
- Make criteria measurable and specific
- Include code quality, testing, performance, and integration metrics
- Always include code quality checks (ruff, mypy, pre-commit)
- End with what foundation this provides for future work

**Further Implementation Details**:
- Use this section for complex implementations that need detailed analysis
- Include problem analysis with specific code references (file:line)
- Provide before/after code examples showing the transformation
- Quantify benefits with specific metrics and percentages
- Include detailed testing strategies with code examples
- Add migration/rollout strategies for complex changes
- Use emojis to organize sections for better readability

### Best Practices:

1. **Atomic Steps**: Each plan should represent one logical implementation unit
2. **Clear Dependencies**: Explicitly state what must exist before starting
3. **Comprehensive Testing**: Include both unit and integration test requirements
4. **Pattern Consistency**: Reference existing patterns to follow
5. **Future Ready**: Consider how this step enables future development
6. **Measurable Success**: Define clear, testable success criteria
