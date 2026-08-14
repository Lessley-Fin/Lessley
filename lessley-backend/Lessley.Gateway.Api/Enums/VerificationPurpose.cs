namespace Lessley.Gateway.Api.Enums;

/// <summary>Which flow an emailed one-time code belongs to. A code is only valid for its own purpose.</summary>
public enum VerificationPurpose
{
    PasswordReset,
    LoginOtp,
}
