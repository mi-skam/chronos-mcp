"""CalDAV component search functionality for Chronos MCP (Events, Tasks, Journals)."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SearchOptions:
    """Options for CalDAV component search functionality."""

    query: str
    fields: list[str]
    component_types: list[str] = field(default_factory=lambda: ["VEVENT"])
    case_sensitive: bool = False
    match_type: str = "contains"
    use_regex: bool = False
    date_start: datetime | None = None
    date_end: datetime | None = None
    max_results: int | None = None

    def __post_init__(self):
        valid_types = ["contains", "starts_with", "ends_with", "exact", "regex"]
        if self.match_type not in valid_types:
            raise ValueError(f"match_type must be one of {valid_types}")

        valid_components = ["VEVENT", "VTODO", "VJOURNAL"]
        for comp_type in self.component_types:
            if comp_type not in valid_components:
                raise ValueError(f"component_type must be one of {valid_components}")

        # Set default fields based on component types if not provided
        if not self.fields:
            self.fields = self._get_default_fields()

        if self.use_regex or self.match_type == "regex":
            flags = 0 if self.case_sensitive else re.IGNORECASE
            self.pattern = re.compile(self.query, flags)

    def _get_default_fields(self) -> list[str]:
        """Get default search fields based on component types."""
        fields = {"summary", "description"}  # Common fields

        if "VEVENT" in self.component_types:
            fields.update(["location"])

        if "VTODO" in self.component_types:
            fields.update(["due", "priority", "status", "percent_complete"])

        if "VJOURNAL" in self.component_types:
            fields.update(["dtstart", "categories"])

        return list(fields)


def _matches_component_type(component: dict[str, Any], options: SearchOptions) -> bool:
    """Check if component matches the requested component types."""
    component_type = component.get(
        "component_type", "VEVENT"
    )  # Default to VEVENT for backward compatibility

    # For legacy support, try to infer component type from fields
    if component_type == "VEVENT" and not component.get("component_type"):
        if (
            "due" in component
            or "priority" in component
            or "percent_complete" in component
        ):
            component_type = "VTODO"
        elif (
            "dtstart" in component
            and "categories" in component
            and not component.get("dtend")
        ):
            component_type = "VJOURNAL"

    return component_type in options.component_types


def search_components(
    components: list[dict[str, Any]], options: SearchOptions
) -> list[dict[str, Any]]:
    """Search CalDAV components (events, tasks, journals) based on provided options."""
    if not options.query and not (options.date_start or options.date_end):
        # Filter by component type even if no query
        return [comp for comp in components if _matches_component_type(comp, options)]

    def matches_text(component: dict[str, Any]) -> bool:
        if not options.query:
            return True

        for search_field in options.fields:
            value = component.get(search_field, "")
            if value is None:
                continue

            # Handle special field formatting
            if search_field == "categories" and isinstance(value, list):
                value_str = " ".join(str(v) for v in value)
            elif search_field in ["priority", "percent_complete"] and value is not None:
                value_str = str(value)
            else:
                value_str = str(value)

            if not options.case_sensitive:
                value_str = value_str.lower()
                query = options.query.lower()
            else:
                query = options.query

            if options.use_regex or options.match_type == "regex":
                if options.pattern.search(value_str):
                    return True
            elif options.match_type == "contains":
                if query in value_str:
                    return True
            elif options.match_type == "starts_with":
                if value_str.startswith(query):
                    return True
            elif options.match_type == "ends_with":
                if value_str.endswith(query):
                    return True
            elif options.match_type == "exact" and value_str == query:
                return True

        return False

    def matches_date(component: dict[str, Any]) -> bool:
        if not (options.date_start or options.date_end):
            return True

        # Try different date fields based on component type
        date_field = None
        if component.get("component_type") == "VTODO" or "due" in component:
            date_field = component.get("due")
        elif component.get("component_type") == "VJOURNAL" or (
            "dtstart" in component and not component.get("dtend")
        ):
            date_field = component.get("dtstart")
        else:  # VEVENT
            date_field = component.get("dtstart") or component.get("start")

        if not date_field:
            return False

        if isinstance(date_field, str):
            date_field = datetime.fromisoformat(date_field.replace("Z", "+00:00"))

        if options.date_start and date_field < options.date_start:
            return False
        return not (options.date_end and date_field > options.date_end)

    results = [
        component
        for component in components
        if _matches_component_type(component, options)
        and matches_text(component)
        and matches_date(component)
    ]

    if options.max_results:
        results = results[: options.max_results]

    return results


def _get_field_weights() -> dict[str, float]:
    """Return field weights for relevance scoring."""
    return {
        "summary": 3.0,
        "description": 2.0,
        "location": 1.0,
        "due": 2.5,
        "priority": 1.5,
        "status": 1.0,
        "percent_complete": 1.0,
        "dtstart": 2.0,
        "categories": 1.5,
    }


def _format_field_value(field: str, value: Any, case_sensitive: bool) -> str:
    """Format field value for scoring."""
    if field == "categories" and isinstance(value, list):
        value_str = " ".join(str(v) for v in value)
    elif field in ["priority", "percent_complete"] and value is not None:
        value_str = str(value)
    else:
        value_str = str(value)

    if not case_sensitive:
        value_str = value_str.lower()

    return value_str


def _calculate_regex_score(value_str: str, pattern: Any) -> float:
    """Calculate score for regex matches."""
    matches = list(pattern.finditer(value_str))
    if not matches:
        return 0.0

    field_score = 2.0 * len(matches)
    first_match_pos = matches[0].start()
    position_factor = 1.0 - (first_match_pos / max(len(value_str), 1))
    return field_score * (1.0 + position_factor * 0.5)


def _calculate_text_match_score(value_str: str, query: str, match_type: str) -> float:
    """Calculate score for text matches."""
    if match_type == "exact" and value_str == query:
        return 5.0

    if match_type == "starts_with" and value_str.startswith(query):
        return 3.0

    if match_type == "contains" or query in value_str:
        occurrences = value_str.count(query)
        if occurrences > 0:
            field_score = 1.0 * occurrences
            first_pos = value_str.find(query)
            position_factor = 1.0 - (first_pos / max(len(value_str), 1))
            return field_score * (1.0 + position_factor * 0.5)

    return 0.0


def _get_component_date_field(component: dict[str, Any]) -> Any:
    """Extract the appropriate date field based on component type."""
    if component.get("component_type") == "VTODO" or "due" in component:
        return component.get("due")

    if component.get("component_type") == "VJOURNAL" or (
        "dtstart" in component and not component.get("dtend")
    ):
        return component.get("dtstart")

    # VEVENT
    return component.get("dtstart") or component.get("start")


def _calculate_recency_boost(date_field: Any, current_time: datetime) -> float:
    """Calculate recency boost for scoring."""
    if not date_field:
        return 1.0

    if isinstance(date_field, str):
        date_field = datetime.fromisoformat(date_field.replace("Z", "+00:00"))

    days_diff = abs((current_time - date_field).days)
    if days_diff <= 30:
        recency_boost = 0.1 * (1.0 - days_diff / 30.0)
        return 1.0 + recency_boost

    return 1.0


def calculate_relevance_score(
    component: dict[str, Any],
    options: SearchOptions,
    current_time: datetime | None = None,
) -> float:
    """Calculate relevance score for search ranking."""
    if current_time is None:
        current_time = datetime.now()

    score = 0.0
    query = options.query.lower() if not options.case_sensitive else options.query
    field_weights = _get_field_weights()

    for search_field in options.fields:
        if search_field not in field_weights:
            continue

        value = component.get(search_field, "")
        if not value:
            continue

        value_str = _format_field_value(search_field, value, options.case_sensitive)

        if options.use_regex or options.match_type == "regex":
            field_score = _calculate_regex_score(value_str, options.pattern)
        else:
            field_score = _calculate_text_match_score(
                value_str, query, options.match_type
            )

        score += field_score * field_weights.get(search_field, 1.0)

    # Apply recency boost
    date_field = _get_component_date_field(component)
    recency_multiplier = _calculate_recency_boost(date_field, current_time)
    score *= recency_multiplier

    return score


def search_components_ranked(
    components: list[dict[str, Any]], options: SearchOptions
) -> list[tuple[dict[str, Any], float]]:
    """Search CalDAV components and return them with relevance scores."""
    matching_components = search_components(components, options)

    scored_components = []
    for component in matching_components:
        score = calculate_relevance_score(component, options)
        scored_components.append((component, score))

    scored_components.sort(key=lambda x: x[1], reverse=True)

    if options.max_results:
        scored_components = scored_components[: options.max_results]

    return scored_components


# Backward compatibility functions
def search_events(
    events: list[dict[str, Any]], options: SearchOptions
) -> list[dict[str, Any]]:
    """Search events - backward compatibility wrapper."""
    # Ensure we're only searching events for backward compatibility
    event_options = SearchOptions(
        query=options.query,
        fields=options.fields,
        component_types=["VEVENT"],
        case_sensitive=options.case_sensitive,
        match_type=options.match_type,
        use_regex=options.use_regex,
        date_start=options.date_start,
        date_end=options.date_end,
        max_results=options.max_results,
    )
    return search_components(events, event_options)


def search_events_ranked(
    events: list[dict[str, Any]], options: SearchOptions
) -> list[tuple[dict[str, Any], float]]:
    """Search events and return them with relevance scores - backward compatibility wrapper."""
    # Ensure we're only searching events for backward compatibility
    event_options = SearchOptions(
        query=options.query,
        fields=options.fields,
        component_types=["VEVENT"],
        case_sensitive=options.case_sensitive,
        match_type=options.match_type,
        use_regex=options.use_regex,
        date_start=options.date_start,
        date_end=options.date_end,
        max_results=options.max_results,
    )
    return search_components_ranked(events, event_options)
