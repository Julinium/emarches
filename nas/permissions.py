def allow_profile_owner(request, private_file):
    return private_file.parent_object.user == request.user