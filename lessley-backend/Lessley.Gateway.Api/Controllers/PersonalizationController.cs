// All Personalization proxy endpoints removed (task 4).
// Clients call the Personalization service directly for insights and recommendations.
// The Gateway's only Personalization interaction is the internal RecalculateCategoriesAsync
// call triggered from UserController (PATCH /api/user/{email} and POST /api/user/{email}/recalculate).
