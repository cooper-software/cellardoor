from cellardoor.authorization import identity

admin_or_self = (identity.role == 'admin') | (item.id == identity.id)
admin_or_user = (identity.role == 'admin') | (identity.role == 'user')