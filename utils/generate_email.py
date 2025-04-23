def generate_email(full_name: str, university_id: str) -> str:
    """
    Converts 'Nahom Merga Woldeyes' + 'UGR/3345/16' 
    -> 'nahom.ugr-3345-16@aau.edu.et'
    """
    first_name = full_name.strip().split()[0].lower()
    formatted_id = university_id.lower().replace("/", "-")
    return f"{first_name}.{formatted_id}@aau.edu.et"
