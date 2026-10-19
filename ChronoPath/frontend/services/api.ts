import axios from "axios";
import { GenerateRequest, GenerateResponse, Journey, Profile } from "../types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production" ? "/api" : "http://localhost:8000");

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

import { auth } from "./firebase";

// Automatic Authentication Interceptor
apiClient.interceptors.request.use(async (config) => {
  if (config.url === "/generate") {
    const user = auth.currentUser;
    if (user) {
      try {
        const token = await user.getIdToken(true);
        config.headers.Authorization = `Bearer ${token}`;
      } catch (err) {
        console.error("Failed to get Firebase token", err);
      }
    } else {
        console.warn("No authenticated user, request to /generate may fail.");
    }
  }
  return config;
});

export const health = async (): Promise<{ status: string; app: string; environment: string }> => {
  const response = await apiClient.get("/health");
  return response.data;
};

export const generateStory = async (data: GenerateRequest): Promise<GenerateResponse> => {
  const response = await apiClient.post<GenerateResponse>("/generate", data);
  return response.data;
};

export const sendFeedback = async (requestId: string, rating: number): Promise<void> => {
  await apiClient.post("/feedback", { request_id: requestId, rating });
};

// Client-side local storage wrappers for profile and journey persistence since backend currently lacks them
const PROFILE_KEY = "nomadnotes_profile";
const JOURNEY_KEY = "nomadnotes_journey_history";

export const getProfile = async (): Promise<Profile> => {
  if (typeof window === "undefined") {
    return { preferredLanguage: "English", storiesViewedCount: 0, placesVisitedCount: 0 };
  }
  const data = localStorage.getItem(PROFILE_KEY);
  if (data) {
    return JSON.parse(data);
  }
  const defaultProfile: Profile = {
    preferredLanguage: "English",
    storiesViewedCount: 0,
    placesVisitedCount: 0,
    age: 25,
    origin: "Global Explorer",
    background: "Curious history enthusiast interested in architecture and local heritage.",
    name: "Traveler"
  };
  localStorage.setItem(PROFILE_KEY, JSON.stringify(defaultProfile));
  return defaultProfile;
};

export const updateProfile = async (profile: Partial<Profile>): Promise<Profile> => {
  const current = await getProfile();
  const updated = { ...current, ...profile };
  localStorage.setItem(PROFILE_KEY, JSON.stringify(updated));
  return updated;
};

export const getJourney = async (): Promise<Journey[]> => {
  if (typeof window === "undefined") return [];
  const data = localStorage.getItem(JOURNEY_KEY);
  if (data) {
    return JSON.parse(data);
  }
  
  // Return some initial historic spots as default history
  const defaultJourney: Journey[] = [
    {
      id: "j-1",
      date: "Today",
      places: [
        {
          id: "p-1",
          name: "Shaniwar Wada",
          latitude: 18.5196,
          longitude: 73.8553,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          storyTitle: "Peshwa Era Citadel"
        },
        {
          id: "p-2",
          name: "Lal Mahal",
          latitude: 18.5205,
          longitude: 73.8562,
          timestamp: new Date(Date.now() - 3600000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          storyTitle: "Chhatrapati Shivaji Maharaj's Childhood Home"
        }
      ]
    },
    {
      id: "j-2",
      date: "Yesterday",
      places: [
        {
          id: "p-3",
          name: "Aga Khan Palace",
          latitude: 18.5524,
          longitude: 73.9015,
          timestamp: "03:15 PM",
          storyTitle: "Italian Arches and Freedom Fighters"
        }
      ]
    }
  ];
  localStorage.setItem(JOURNEY_KEY, JSON.stringify(defaultJourney));
  return defaultJourney;
};

export const savePlaceToJourney = async (placeName: string, title: string, lat: number, lng: number): Promise<Journey[]> => {
  const journeys = await getJourney();
  const todayLabel = "Today";
  
  const newPlace = {
    id: `p-${Date.now()}`,
    name: placeName,
    latitude: lat,
    longitude: lng,
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    storyTitle: title
  };

  let todayJourney = journeys.find(j => j.date === todayLabel);

  if (todayJourney) {
    // Avoid duplicate checkins for same place name recently
    if (!todayJourney.places.some(p => p.name.toLowerCase() === placeName.toLowerCase())) {
      todayJourney.places.unshift(newPlace);
    }
  } else {
    todayJourney = {
      id: `j-${Date.now()}`,
      date: todayLabel,
      places: [newPlace]
    };
    journeys.unshift(todayJourney);
  }

  localStorage.setItem(JOURNEY_KEY, JSON.stringify(journeys));
  
  // Also increment profile counts
  const profile = await getProfile();
  await updateProfile({
    storiesViewedCount: profile.storiesViewedCount + 1,
    placesVisitedCount: profile.placesVisitedCount + 1,
  });

  return journeys;
};
