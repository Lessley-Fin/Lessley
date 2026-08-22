import {
  Easing,
  Img,
  Interactive,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { fontFamily } from "../font";
import { typed } from "../helpers";

const USERNAME = "roeecr";

/** LoginPage.tsx at video scale: types credentials, then signs in. */
export const LoginScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const username = typed(USERNAME, frame, 20, 0.22);
  const passwordDots = "•".repeat(
    Math.max(0, Math.min(9, Math.floor((frame - 60) * 0.32))),
  );

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "0 56px",
        fontFamily,
        color: "#182634",
        backgroundColor: "#F5F9FB",
      }}
    >
      <Img
        src={staticFile("logo-without-name.svg")}
        style={{
          width: 132,
          height: 132,
          alignSelf: "center",
          marginBottom: 26,
          opacity: interpolate(frame, [0, 16], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          scale: interpolate(frame, [0, 34], [0.6, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.spring({ damping: 12 }),
            output: "perceptual-scale",
          }),
        }}
      />

      <p
        style={{
          margin: 0,
          fontSize: 46,
          fontWeight: 800,
          letterSpacing: "-0.03em",
          textAlign: "center",
        }}
      >
        Welcome back
      </p>
      <p
        style={{
          margin: "8px 0 0",
          fontSize: 23,
          color: "#687682",
          textAlign: "center",
        }}
      >
        Financial autopilot for every purchase
      </p>

      <div style={{ height: 44 }} />

      <Field
        value={username}
        placeholder="Username or email"
        showCaret={frame >= 20 && username.length < USERNAME.length}
      />
      <div style={{ height: 18 }} />
      <Field
        value={passwordDots}
        placeholder="Password"
        showCaret={frame >= 60 && passwordDots.length < 9}
      />

      <p
        style={{
          margin: "16px 4px 0",
          fontSize: 21,
          fontWeight: 600,
          color: "#397C7F",
          textAlign: "right",
        }}
      >
        Forgot password?
      </p>

      <Interactive.Div
        name="Sign in button"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 94,
          marginTop: 28,
          borderRadius: 999,
          background: "linear-gradient(135deg, #45939B 0%, #367680 100%)",
          color: "#F2FAFA",
          fontSize: 28,
          fontWeight: 700,
          boxShadow: "0 12px 28px rgba(54,118,128,0.35)",
          scale: interpolate(frame, [94, 102, 114], [1, 0.955, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.4, 0, 0.6, 1),
            output: "perceptual-scale",
          }),
        }}
      >
        {frame >= 102 ? "Signing in..." : "Sign in"}
      </Interactive.Div>

      <p
        style={{
          margin: "24px 0 0",
          fontSize: 23,
          fontWeight: 600,
          color: "#397C7F",
          textAlign: "center",
        }}
      >
        Create account
      </p>
    </div>
  );
};

const Field: React.FC<{
  value: string;
  placeholder: string;
  showCaret: boolean;
}> = ({ value, placeholder, showCaret }) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        height: 92,
        padding: "0 28px",
        borderRadius: 26,
        backgroundColor: "#FFFFFF",
        border: value ? "2px solid #397C7F" : "2px solid #DDE5E9",
        fontSize: 26,
        color: value ? "#182634" : "#95A2AC",
        letterSpacing: value.startsWith("•") ? "0.18em" : "normal",
      }}
    >
      {value || placeholder}
      {showCaret ? (
        <span
          style={{
            display: "inline-block",
            width: 3,
            height: 32,
            marginLeft: 3,
            backgroundColor: "#397C7F",
          }}
        />
      ) : null}
    </div>
  );
};
